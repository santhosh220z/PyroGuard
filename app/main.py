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
        "status": "running"
    }


def create_app():
    """Create and configure the FastAPI application"""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.routes import router
    from app.api.profile import router as profile_router
    from app.config.security import setup_rate_limiter, get_cors_origins
    from app.database import init_db

    @asynccontextmanager
    async def lifespan(app):
        # Initialize database
        init_db()
        print("Database initialized")
        
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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiter
    setup_rate_limiter(app)

    # API routes
    app.include_router(router)
    app.include_router(profile_router)

    # Dashboard static files (public access)
    dashboard_dist = PROJECT_ROOT / "pyroguard ui" / "dist"
    if dashboard_dist.exists():
        assets_dir = dashboard_dist / "assets"
        if assets_dir.exists():
            app.mount("/dashboard/assets", StaticFiles(directory=str(assets_dir)), name="dashboard_assets")

    # Dashboard entry - always serve under trailing slash so the
    # relative "./assets/..." URLs in index.html resolve correctly.
    # Serving index.html at bare "/dashboard" breaks asset resolution
    # (browser resolves ./assets to /assets) -> blank white page.
    @app.get("/dashboard")
    async def dashboard_redirect():
        """Redirect bare /dashboard to /dashboard/ (trailing slash)."""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard/")

    @app.get("/dashboard/")
    async def dashboard_page():
        """Serve dashboard index.html - public access."""
        index_file = dashboard_dist / "index.html"
        if index_file.exists():
            from fastapi.responses import FileResponse
            return FileResponse(str(index_file))
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dashboard not built")

    # Catch-all for dashboard SPA routes (e.g., /dashboard/about)
    @app.get("/dashboard/{path:path}")
    async def dashboard_spa(path: str):
        """Serve dashboard for SPA routes - public access."""
        index_file = dashboard_dist / "index.html"
        if index_file.exists():
            from fastapi.responses import FileResponse
            return FileResponse(str(index_file))
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dashboard not built")

    # Root redirect to dashboard
    @app.get("/")
    async def root_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard/")

    return app


# Initialize on import
project_info = get_project_info()
print(f"PyroGuard v0.1.0 - {project_info['title']}")
print(f"Project: {project_info['name']} - {project_info['type']}")
print(f"Model: {settings.MODEL_PATH}")
print(f"Confidence threshold: {settings.CONFIDENCE_THRESHOLD}")
print(f"Server running at: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000, log_level="info")