# PyroGuard API Routes
import cv2
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

router = APIRouter(tags=["pyroguard"])

# Shared incident database instance (created lazily, reused across requests)
_incident_db = None


def get_incident_db():
    """Get the shared incident database instance."""
    global _incident_db
    if _incident_db is None:
        from app.incidents.incident_db import IncidentDatabase
        from app.config.config import settings
        _incident_db = IncidentDatabase(db_path=settings.DATABASE_PATH)
    return _incident_db


def get_camera_manager():
    """Get the shared camera manager from the live detection service."""
    from app.detection.live_service import get_live_service
    return get_live_service().manager


def _primary_camera_id(manager) -> str:
    """Return the first enabled camera id, or the first camera id."""
    enabled = [c["id"] for c in manager.cameras if c.get("enabled")]
    if enabled:
        return enabled[0]
    return manager.cameras[0]["id"] if manager.cameras else None


@router.get("/camera/stream", summary="MJPEG live camera feed")
async def camera_stream(cam: str = None):
    """Stream a camera feed as multipart JPEG (MJPEG)."""
    import time as _time

    manager = get_camera_manager()
    valid_ids = {c["id"] for c in manager.cameras}
    cam_id = cam if cam in valid_ids else _primary_camera_id(manager)
    if cam_id is None:
        raise HTTPException(status_code=404, detail="No cameras configured")

    from app.detection.live_service import get_live_service
    service = get_live_service()

    def generate():
        while True:
            frame = service.get_frame(cam_id)
            if frame is None:
                _time.sleep(0.2)
                continue
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if not ok:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            )

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/camera/snapshot", summary="Latest camera frame as JPEG")
async def camera_snapshot(cam: str = None):
    """Return the latest camera frame as a single JPEG image."""
    manager = get_camera_manager()
    valid_ids = {c["id"] for c in manager.cameras}
    cam_id = cam if cam in valid_ids else _primary_camera_id(manager)
    from app.detection.live_service import get_live_service
    frame = get_live_service().get_frame(cam_id)
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera frame unavailable")
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise HTTPException(status_code=500, detail="Frame encoding failed")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.post("/camera/demo/upload", summary="Upload a demo video and feed it to the demo camera")
async def upload_demo_video(file: UploadFile = File(...)):
    """Save an uploaded video into demo/ and point the file-based camera at it."""
    from app.config.config import PROJECT_ROOT

    ALLOWED_EXT = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v", ".mpg", ".mpeg"}
    original = Path(file.filename or "demo.mp4")
    ext = original.suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported video type '{ext}'. Allowed: {sorted(ALLOWED_EXT)}")

    demo_dir = PROJECT_ROOT / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", original.stem)[:80] or "demo"
    dest = demo_dir / f"{safe_stem}{ext}"
    counter = 1
    while dest.exists():
        dest = demo_dir / f"{safe_stem}_{counter}{ext}"
        counter += 1

    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not save upload: {e}")
    finally:
        await file.close()

    from app.detection.live_service import get_live_service
    manager = get_live_service().manager

    demo_cam = next(
        (c for c in manager.cameras if c.get("id") == "camera_01" and c.get("enabled")),
        next((c for c in manager.cameras if manager.file_sources.get(c["id"])), None),
    )
    if demo_cam is None:
        raise HTTPException(status_code=404, detail="No demo (file-based) camera configured")

    result = manager.set_source(demo_cam["id"], str(dest))
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "camera_id": demo_cam["id"],
        "filename": dest.name,
        "source": str(dest),
        "status": result.get("status"),
    }


@router.get("/health", summary="Health check endpoint")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pyroguard"}


@router.get("/status", summary="System status")
async def system_status():
    """System status endpoint"""
    from app.config.config import settings
    return {
        "service": "pyroguard",
        "status": "operational",
        "model": settings.MODEL_PATH,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "dry_run": settings.DRY_RUN
    }


@router.get("/detection/live", summary="Live detection state")
async def detection_live():
    """Current real-time detection state from the live detection service."""
    from app.detection.live_service import get_live_service
    return get_live_service().get_live_status()


@router.get("/cameras", summary="List cameras with health status")
async def list_cameras():
    """List configured cameras and their health status."""
    from app.detection.live_service import get_live_service
    manager = get_camera_manager()
    service_fps = get_live_service()._fps
    status_info = {}
    for cam in manager.cameras:
        cam_id = cam["id"]
        cam_status = manager.get_camera_status(cam_id)
        # For cameras not initialized (disabled), show DISABLED instead of ERROR
        if "error" in cam_status and cam_status.get("error") == "Camera not initialized":
            cam_status = {"status": "DISABLED", "failed_frames": 0}
        status_info[cam_id] = {
            "name": cam["name"],
            "enabled": cam["enabled"],
            **cam_status,
            "fps": service_fps.get(cam_id, 0.0),
        }
    return {"cameras": status_info}


@router.get("/incidents", summary="List incidents")
async def list_incidents(status: str = None):
    """List all incidents, optionally filtered by status."""
    db = get_incident_db()
    return {"incidents": db.list_incidents(status=status)}


@router.get("/incidents/{incident_id}", summary="Get incident by ID")
async def get_incident(incident_id: str):
    """Get incident by ID."""
    db = get_incident_db()
    incident = db.get_incident(incident_id)
    if "error" in incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"incident": incident}


@router.post("/incidents/{incident_id}/acknowledge", summary="Acknowledge incident")
async def acknowledge_incident(incident_id: str):
    """Acknowledge an incident."""
    db = get_incident_db()
    success = db.update_status(incident_id, "ACKNOWLEDGED")
    if not success:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"incident_id": incident_id, "status": "ACKNOWLEDGED"}


@router.post("/incidents/{incident_id}/resolve", summary="Resolve incident")
async def resolve_incident(incident_id: str):
    """Resolve an incident."""
    db = get_incident_db()
    success = db.update_status(incident_id, "RESOLVED")
    if not success:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"incident_id": incident_id, "status": "RESOLVED"}


@router.get("/model/status", summary="Model status")
async def model_status():
    """Model status endpoint."""
    from pathlib import Path
    from app.config.config import settings
    from app.detection.detection import is_fire_confirmed, get_confirmation_info

    model_path = Path(settings.MODEL_PATH)
    return {
        "model_path": settings.MODEL_PATH,
        "loaded": model_path.exists(),
        "fire_confirmed": is_fire_confirmed(),
        "confirmation_info": get_confirmation_info()
    }