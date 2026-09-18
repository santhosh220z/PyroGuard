# PyroGuard API Routes
import cv2
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel

from app.config.security import get_current_user, require_operator, require_admin, limiter, rate_limit

router = APIRouter(tags=["pyroguard"])


class AcknowledgeRequest(BaseModel):
    user: str


class ResolveRequest(BaseModel):
    user: str
    false_positive: bool = False


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


# ===== Incident Endpoints =====

@router.get("/incidents", summary="List incidents")
@rate_limit("60/minute")
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    camera_id: Optional[str] = Query(None, description="Filter by camera"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """List incidents with optional filters and pagination."""
    from app.incidents import incident_manager
    incidents = incident_manager.list_incidents(
        status=status,
        camera_id=camera_id,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    total = incident_manager.get_stats()["total"]
    return {
        "incidents": incidents,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/incidents/stats", summary="Incident statistics")
@rate_limit("60/minute")
async def incident_stats(user: dict = Depends(get_current_user)):
    """Get incident statistics for dashboard."""
    from app.incidents import incident_manager
    return incident_manager.get_stats()


@router.get("/incidents/{incident_id}", summary="Get incident details")
@rate_limit("60/minute")
async def get_incident(incident_id: int, user: dict = Depends(get_current_user)):
    """Get detailed incident information."""
    from app.incidents import incident_manager
    incident = incident_manager.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Get alerts and audit logs
    from app.database import get_db_session, get_alerts_for_incident, get_audit_logs
    with get_db_session() as db:
        alerts = get_alerts_for_incident(db, incident_id)
        audit_logs = get_audit_logs(db, incident_id)
    
    incident["alerts"] = [
        {
            "id": a.id,
            "provider": a.provider,
            "status": a.status.value,
            "recipient": a.recipient,
            "error_message": a.error_message,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
        }
        for a in alerts
    ]
    incident["audit_logs"] = [
        {
            "id": log.id,
            "action": log.action,
            "performed_by": log.performed_by,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in audit_logs
    ]
    return incident


@router.get("/incidents/{incident_id}/snapshot", summary="Get incident snapshot")
@rate_limit("60/minute")
async def get_incident_snapshot(incident_id: int, user: dict = Depends(get_current_user)):
    """Get the incident snapshot image."""
    from app.incidents import incident_manager
    incident = incident_manager.get_incident(incident_id)
    if not incident or not incident.get("snapshot_path"):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    from pathlib import Path
    snapshot_path = Path(incident["snapshot_path"])
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot file not found")
    
    return FileResponse(snapshot_path, media_type="image/jpeg")


@router.post("/incidents/{incident_id}/acknowledge", summary="Acknowledge incident")
@rate_limit("30/minute")
async def acknowledge_incident_endpoint(
    incident_id: int,
    request: AcknowledgeRequest,
    user: dict = Depends(require_operator),
):
    """Acknowledge an incident."""
    from app.incidents import incident_manager
    success = incident_manager.acknowledge(incident_id, request.user or user["sub"])
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"success": True, "message": "Incident acknowledged"}


@router.post("/incidents/{incident_id}/resolve", summary="Resolve incident")
@rate_limit("30/minute")
async def resolve_incident_endpoint(
    incident_id: int,
    request: ResolveRequest,
    user: dict = Depends(require_operator),
):
    """Resolve an incident (or mark as false positive)."""
    from app.incidents import incident_manager
    success = incident_manager.resolve(incident_id, request.user or user["sub"], request.false_positive)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"success": True, "message": "Incident resolved"}


# ===== Alert Test Endpoint =====

@router.post("/alerts/test", summary="Test all enabled alert channels")
@rate_limit("3/minute")
async def test_alerts(user: dict = Depends(require_admin)):
    """Test alert channels (DRY_RUN safe)."""
    from app.config.config import settings
    from app.alerts import get_providers
    
    if not settings.DRY_RUN:
        return {"warning": "DRY_RUN=false - this will send real alerts!"}
    
    providers = get_providers(settings.get_alert_config())
    if not providers:
        return {"message": "No alert channels configured", "enabled": []}
    
    test_incident = {
        "id": "test",
        "camera_id": "camera_01",
        "camera_name": "Test Camera",
        "confidence": 0.85,
        "class_name": "fire",
        "severity": "high",
        "detected_at": datetime.utcnow().isoformat(),
    }
    
    results = []
    for provider in providers:
        result = await provider.send(test_incident)
        results.append({
            "provider": result.provider,
            "success": result.success,
            "recipient": result.recipient,
            "error": result.error,
        })
    
    return {"results": results}
