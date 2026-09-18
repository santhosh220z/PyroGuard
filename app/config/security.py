"""Security utilities: JWT, API keys, rate limiting, CORS."""
import os
import time
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import jwt, JWTError
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from app.config.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# API Key settings
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEYS = {}
if os.getenv("API_KEYS"):
    # Format: "key1:role1,key2:role2"
    for pair in os.getenv("API_KEYS", "").split(","):
        if ":" in pair:
            k, r = pair.split(":", 1)
            API_KEYS[k.strip()] = r.strip()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security scheme
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature for webhook payloads."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(API_KEY_HEADER),
) -> Dict[str, Any]:
    """Get current authenticated user from JWT or API key."""
    # Try JWT first
    if credentials:
        payload = verify_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            return {"sub": payload.get("sub"), "role": payload.get("role", "viewer"), "auth_type": "jwt"}
    
    # Try API key
    if api_key and api_key in API_KEYS:
        return {"sub": api_key[:8], "role": API_KEYS[api_key], "auth_type": "api_key"}
    
    # No valid auth
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*allowed_roles: str):
    """Dependency factory for role-based access control."""
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' not authorized. Required: {allowed_roles}"
            )
        return user
    return role_checker


def rate_limit(limit: str):
    """Decorator for rate limiting endpoints. Endpoint must accept a `request: Request` parameter."""
    def decorator(func):
        @wraps(func)
        @limiter.limit(limit)
        async def wrapper(request: Request, *args, **kwargs):
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_cors_origins() -> list:
    """Get allowed CORS origins from environment."""
    origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
    return [o.strip() for o in origins.split(",") if o.strip()]


def setup_rate_limiter(app):
    """Attach rate limiter to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)