# PyroGuard - AI Fire Detection & Alert Automation
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
        "title": "AI Fire Detection & Alert Automation",
        "type": "AI-powered real-time safety automation",
        "status": "initializing"
    }

def create_app():
    """Create and configure the FastAPI application"""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from app.api.routes import router
    
    app = FastAPI(
        title="PyroGuard API",
        description="AI-powered real-time fire and smoke detection automation",
        version="0.1.0"
    )
    
    app.include_router(router)
    
    dashboard_dirs = [
        PROJECT_ROOT / "pyroguard ui" / "dist",
        PROJECT_ROOT / "dashboard",
    ]
    for dashboard_dir in dashboard_dirs:
        if dashboard_dir.exists():
            app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")
            break
    
    return app

# Initialize on import
project_info = get_project_info()
print(f"PyroGuard v0.1.0 - {project_info['title']}")
print(f"Project: {project_info['name']} - {project_info['type']}")
print(f"Model: {settings.MODEL_PATH}")
print(f"Confidence threshold: {settings.CONFIDENCE_THRESHOLD}")