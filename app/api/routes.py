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
    return {"service": "pyroguard", "status": "operational"}

@router.get("/cameras", summary="List cameras")
async def list_cameras():
    """List configured cameras"""
    return {"cameras": []}

@router.get("/incidents", summary="List incidents")
async def list_incidents():
    """List all incidents"""
    return {"incidents": []}

@router.get("/incidents/{incident_id}", summary="Get incident by ID")
async def get_incident(incident_id: str):
    """Get incident by ID"""
    return {"incident_id": incident_id, "status": "not_found"}

@router.post("/incidents/{incident_id}/acknowledge", summary="Acknowledge incident")
async def acknowledge_incident(incident_id: str):
    """Acknowledge incident"""
    return {"incident_id": incident_id, "status": "acknowledged"}

@router.post("/incidents/{incident_id}/resolve", summary="Resolve incident")
async def resolve_incident(incident_id: str):
    """Resolve incident"""
    return {"incident_id": incident_id, "status": "resolved"}

@router.get("/model/status", summary="Model status")
async def model_status():
    """Model status endpoint"""
    return {"model": "not_loaded", "status": "unavailable"}