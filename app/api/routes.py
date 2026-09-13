# PyroGuard API Routes
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["pyroguard"])

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

@router.get("/cameras", summary="List cameras")
async def list_cameras():
    """List configured cameras"""
    from app.cameras.camera_manager import CameraManager
    manager = CameraManager()
    status_info = {}
    for cam_id in ["camera_01", "camera_02"]:
        status_info[cam_id] = manager.get_camera_status(cam_id)
    return {"cameras": status_info}

@router.get("/incidents", summary="List incidents")
async def list_incidents():
    """List all incidents"""
    from app.database.incident_db import IncidentDatabase
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db = IncidentDatabase(db_path=db_path)
        incidents = db.list_incidents()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    return {"incidents": incidents}

@router.get("/incidents/{incident_id}", summary="Get incident by ID")
async def get_incident(incident_id: str):
    """Get incident by ID"""
    from app.database.incident_db import IncidentDatabase
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db = IncidentDatabase(db_path=db_path)
        incident = db.get_incident(incident_id)
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    return {"incident": incident}

@router.post("/incidents/{incident_id}/acknowledge", summary="Acknowledge incident")
async def acknowledge_incident(incident_id: str):
    """Acknowledge incident"""
    from app.database.incident_db import IncidentDatabase
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db = IncidentDatabase(db_path=db_path)
        success = db.update_status(incident_id, "ACKNOWLEDGED")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    return {"incident_id": incident_id, "acknowledged": success, "status": "ACKNOWLEDGED"}

@router.post("/incidents/{incident_id}/resolve", summary="Resolve incident")
async def resolve_incident(incident_id: str):
    """Resolve incident"""
    from app.database.incident_db import IncidentDatabase
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db = IncidentDatabase(db_path=db_path)
        success = db.update_status(incident_id, "RESOLVED")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
    return {"incident_id": incident_id, "resolved": success, "status": "RESOLVED"}

@router.get("/model/status", summary="Model status")
async def model_status():
    """Model status endpoint"""
    from app.detection.detection import is_fire_confirmed, get_confirmation_info
    return {
        "model": "YOLOv8",
        "loaded": True,
        "fire_confirmed": is_fire_confirmed(),
        "confirmation_info": get_confirmation_info()
    }