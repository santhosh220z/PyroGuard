# PyroGuard API Routes
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["pyroguard"])

# Shared incident database instance (created lazily, reused across requests)
_incident_db = None


def get_incident_db():
    """Get the shared incident database instance."""
    global _incident_db
    if _incident_db is None:
        from app.incidents.incident_db import IncidentDatabase
        from app.config.config import settings
        _incident_db = IncidentDatabase(db_path=settings.DATABASE_URL.replace("sqlite:///", ""))
    return _incident_db


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


@router.get("/cameras", summary="List cameras with health status")
async def list_cameras():
    """List configured cameras and their health status."""
    from app.cameras.camera_manager import CameraManager
    manager = CameraManager()
    status_info = {}
    for cam in manager.cameras:
        cam_id = cam["id"]
        status_info[cam_id] = {
            "name": cam["name"],
            "enabled": cam["enabled"],
            **manager.get_camera_status(cam_id)
        }
    manager.release_all()
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