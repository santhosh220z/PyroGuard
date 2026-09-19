"""Authentication API routes: login, token refresh, user info."""
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
    get_current_user,
    require_role,
)
from app.config.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store (replace with DB in production)
# Format: username -> {"hash": bcrypt_hash, "role": "admin|operator|viewer"}
USERS = {}

# Initialize default admin (in-memory, dev default; replace with DB seed in prod)
default_admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "changeme123")
USERS["admin"] = {"hash": get_password_hash(default_admin_pass), "role": "admin"}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return access + refresh tokens."""
    user = USERS.get(request.username)
    if not user or not verify_password(request.password, user["hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        {"sub": request.username, "role": user["role"]},
        expires_delta=timedelta(minutes=15),
    )
    refresh_token = create_refresh_token({"sub": request.username, "role": user["role"]})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token."""
    payload = verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    username = payload.get("sub")
    role = payload.get("role", "viewer")

    # Verify user still exists
    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    access_token = create_access_token(
        {"sub": username, "role": role},
        expires_delta=timedelta(minutes=15),
    )
    new_refresh_token = create_refresh_token({"sub": username, "role": role})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserInfo(username=user["sub"], role=user["role"])


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return {"message": "Logged out successfully. Remove tokens client-side."}


# Dependency for admin-only routes
require_admin = require_role("admin")
require_operator = require_role("admin", "operator")