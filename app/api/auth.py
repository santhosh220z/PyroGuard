"""Authentication API routes: login, token refresh, user info, signup."""
import os
import re
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response, Request
from pydantic import BaseModel, field_validator

from app.config.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
    get_current_user,
    require_role,
    rate_limit,
)
from app.config.config import settings
from app.database import get_db, get_user, create_user, update_last_login, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

# Password policy regex (at least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special)
PASSWORD_POLICY = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$")
COMMON_PASSWORDS = {"password", "12345678", "qwerty123", "admin123", "changeme123", "password123"}


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]{3,32}$", v):
            raise ValueError("Username must be 3-32 characters, alphanumeric, underscore, or hyphen")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v in COMMON_PASSWORDS:
            raise ValueError("Password is too common")
        if not PASSWORD_POLICY.match(v):
            raise ValueError("Password must be 8+ chars with upper, lower, digit, and special character")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        valid = {"viewer", "operator", "admin"}
        if v not in valid:
            raise ValueError(f"Role must be one of: {', '.join(valid)}")
        return v


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


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly Secure cookies for tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DRY_RUN,  # Secure=True in prod (HTTPS)
        samesite="lax",
        max_age=900,  # 15 minutes
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DRY_RUN,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
    )


def _clear_auth_cookies(response: Response):
    """Clear auth cookies on logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


@router.post("/login", response_model=TokenResponse)
@rate_limit("5/minute")
async def login(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    """Authenticate user and return access + refresh tokens (accepts form data)."""
    # Rate limiting is handled by middleware, but we can add extra checks here
    user = get_user(db, username.lower())
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    access_token = create_access_token(
        {"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=15),
    )
    refresh_token = create_refresh_token({"sub": user.username, "role": user.role.value})

    update_last_login(db, user.id)
    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/signup", response_model=TokenResponse)
@rate_limit("3/minute")
async def signup(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
    db=Depends(get_db),
):
    """Register a new user and return access + refresh tokens (accepts form data)."""
    # Validate input
    try:
        signup_data = SignupRequest(username=username, password=password, role=role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Check if user exists
    if get_user(db, signup_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Restrict admin role creation - only allow if explicitly enabled via env
    allow_admin_signup = os.getenv("ALLOW_ADMIN_SIGNUP", "false").lower() == "true"
    if signup_data.role == "admin" and not allow_admin_signup:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin registration is not allowed. Contact an administrator.",
        )

    user = create_user(
        db,
        username=signup_data.username,
        password_hash=get_password_hash(signup_data.password),
        role=UserRole(signup_data.role),
    )
    db.commit()

    access_token = create_access_token(
        {"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=15),
    )
    refresh_token = create_refresh_token({"sub": user.username, "role": user.role.value})

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
@rate_limit("10/minute")
async def refresh_token(
    response: Response,
    request: Request,
    refresh_token: str = Form(...),
    db=Depends(get_db),
):
    """Refresh access token using refresh token."""
    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    username = payload.get("sub")
    role = payload.get("role", "viewer")

    # Verify user still exists and is active
    user = get_user(db, username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists or is disabled",
        )

    access_token = create_access_token(
        {"sub": username, "role": role},
        expires_delta=timedelta(minutes=15),
    )
    new_refresh_token = create_refresh_token({"sub": username, "role": role})

    _set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserInfo(username=user["sub"], role=user["role"])


@router.post("/logout")
async def logout(response: Response):
    """Logout endpoint - clears httpOnly cookies."""
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


# Dependency for admin-only routes
require_admin = require_role("admin")
require_operator = require_role("admin", "operator")