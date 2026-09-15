# PyroGuard API Routes
import cv2

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

router = APIRouter(tags=["pyroguard"])


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
async def camera_stream():
    """Stream the primary camera feed as multipart JPEG (MJPEG)."""
    import time as _time

    manager = get_camera_manager()
    cam_id = _primary_camera_id(manager)
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
async def camera_snapshot():
    """Return the latest camera frame as a single JPEG image."""
    manager = get_camera_manager()
    cam_id = _primary_camera_id(manager)
    from app.detection.live_service import get_live_service
    frame = get_live_service().get_frame(cam_id)
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera frame unavailable")
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise HTTPException(status_code=500, detail="Frame encoding failed")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


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
