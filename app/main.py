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
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.routes import router
    from app.api.auth import router as auth_router
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

    # Routers
    app.include_router(router)
    app.include_router(auth_router)

    # Login page at root (handles both login & signup)
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi import Depends, HTTPException, status
    from app.config.security import get_current_user

    @app.get("/", response_class=HTMLResponse)
    async def login_page():
        return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PyroGuard Login</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #0f172a; color: #e2e8f0; }
    .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; width: 100%; max-width: 380px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    h1 { margin: 0 0 0.5rem; font-size: 1.75rem; font-weight: 600; color: #f1f5f9; }
    .subtitle { color: #94a3b8; margin-bottom: 1.5rem; font-size: 0.95rem; }
    .form-group { margin-bottom: 1rem; }
    label { display: block; margin-bottom: 0.4rem; font-size: 0.85rem; color: #cbd5e1; }
    input { width: 100%; padding: 0.7rem 0.9rem; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #f1f5f9; font-size: 1rem; outline: none; transition: border-color 0.15s; }
    input:focus { border-color: #f97316; }
    button { width: 100%; padding: 0.8rem; margin-top: 0.5rem; border: none; border-radius: 8px; background: #f97316; color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.15s; }
    button:hover { background: #ea580c; }
    button.secondary { background: #334155; }
    button.secondary:hover { background: #475569; }
    .error { color: #fca5a5; font-size: 0.85rem; margin-top: 0.5rem; display: none; }
    .error.show { display: block; }
    .footer { margin-top: 1.5rem; text-align: center; font-size: 0.8rem; color: #64748b; }
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
    .tab { flex: 1; padding: 0.6rem; border: none; background: #334155; color: #94a3b8; border-radius: 8px; cursor: pointer; font-weight: 500; transition: all 0.15s; }
    .tab.active { background: #f97316; color: #fff; }
    .form { display: none; }
    .form.active { display: block; }
    .role-select { margin-top: 0.5rem; }
    select { width: 100%; padding: 0.7rem 0.9rem; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #f1f5f9; font-size: 1rem; outline: none; }
  </style>
</head>
<body>
  <div class="card">
    <h1>PyroGuard</h1>
    <p class="subtitle">Fire & Smoke Detection</p>
    
    <div class="tabs">
      <button class="tab active" data-tab="login">Sign In</button>
      <button class="tab" data-tab="signup">Sign Up</button>
    </div>

    <form id="loginForm" class="form active">
      <div class="form-group">
        <label for="username">Username</label>
        <input type="text" id="username" name="username" value="admin" required autocomplete="username" />
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" value="changeme123" required autocomplete="current-password" />
      </div>
      <button type="submit">Sign in</button>
      <div id="loginError" class="error"></div>
    </form>

    <form id="signupForm" class="form">
      <div class="form-group">
        <label for="su_username">Username</label>
        <input type="text" id="su_username" name="username" required autocomplete="username" minlength="3" maxlength="32" />
      </div>
      <div class="form-group">
        <label for="su_password">Password</label>
        <input type="password" id="su_password" name="password" required autocomplete="new-password" minlength="8" />
      </div>
      <div class="form-group role-select">
        <label for="su_role">Role</label>
        <select id="su_role" name="role">
          <option value="viewer">Viewer (read-only)</option>
          <option value="operator">Operator (acknowledge incidents)</option>
          <option value="admin">Admin (full access)</option>
        </select>
      </div>
      <button type="submit">Create Account</button>
      <div id="signupError" class="error"></div>
    </form>

    <p class="footer">Default admin: admin / changeme123 (set DEFAULT_ADMIN_PASSWORD to change)</p>
  </div>
  <script>
    // Tab switching
    document.querySelectorAll('.tab').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'))
        document.querySelectorAll('.form').forEach(f => f.classList.remove('active'))
        btn.classList.add('active')
        document.getElementById(btn.dataset.tab + 'Form').classList.add('active')
      })
    })

    async function authRequest(endpoint, form) {
      const errorEl = document.getElementById(form.id + 'Error')
      errorEl.classList.remove('show')
      const data = new URLSearchParams()
      const formData = new FormData(form)
      for (const [key, value] of formData.entries()) {
        data.append(key, value)
      }
      try {
        const res = await fetch('/auth' + endpoint, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, 
          body: data,
          credentials: 'include'  // Include cookies
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Request failed')
        }
        // Cookies are set automatically by server (httpOnly)
        // Just redirect to dashboard
        window.location.href = '/dashboard/'
      } catch (err) {
        errorEl.textContent = err.message
        errorEl.classList.add('show')
      }
    }

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
      e.preventDefault()
      await authRequest('/login', e.target)
    })

    document.getElementById('signupForm').addEventListener('submit', async (e) => {
      e.preventDefault()
      await authRequest('/signup', e.target)
    })
  </script>
</body>
</html>
        """

    # Serve dashboard assets (JS/CSS) publicly
    dashboard_dist = PROJECT_ROOT / "pyroguard ui" / "dist"
    if dashboard_dist.exists():
        assets_dir = dashboard_dist / "assets"
        if assets_dir.exists():
            app.mount("/dashboard/assets", StaticFiles(directory=str(assets_dir)), name="dashboard_assets")

    # Protected dashboard route - requires authentication
    @app.get("/dashboard")
    @app.get("/dashboard/")
    async def dashboard_page(user: dict = Depends(get_current_user)):
        """Serve dashboard index.html - requires valid JWT token."""
        index_file = dashboard_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Dashboard not built")

    # Catch-all for dashboard SPA routes (e.g., /dashboard/about)
    @app.get("/dashboard/{path:path}")
    async def dashboard_spa(path: str, user: dict = Depends(get_current_user)):
        """Serve dashboard for SPA routes - requires valid JWT token."""
        index_file = dashboard_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Dashboard not built")

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