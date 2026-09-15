# PyroGuard - AI Fire & Smoke Detection
# Main application entry point

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.config import settings

def get_project_info():
    """Return project information"""
    return {
        "name": "PyroGuard",
        "title": "AI Fire & Smoke Detection",
        "type": "AI-powered real-time fire and smoke detection",
        "status": "initializing"
    }

def create_app():
    """Create and configure the FastAPI application"""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from app.api.routes import router

    @asynccontextmanager
    async def lifespan(app):
        # Start the live detection background thread (single camera reader).
        from app.detection.live_service import get_live_service
        service = get_live_service()
        service.start()
        yield
        service.stop()

    app = FastAPI(
        title="PyroGuard API",
        description="AI-powered real-time fire and smoke detection",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    app.include_router(router)
    
    dashboard_dist = PROJECT_ROOT / "pyroguard ui" / "dist"
    if dashboard_dist.exists():
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_dist), html=True), name="dashboard")
    
    return app

# Initialize on import
project_info = get_project_info()
print(f"PyroGuard v0.1.0 - {project_info['title']}")
print(f"Project: {project_info['name']} - {project_info['type']}")
print(f"Model: {settings.MODEL_PATH}")
print(f"Confidence threshold: {settings.CONFIDENCE_THRESHOLD}")