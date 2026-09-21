"""Security utilities: rate limiting, webhook verification, CORS."""
import os
import time
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import APIKeyHeader
import bcrypt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from app.config.config import settings

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password (bcrypt, 12 rounds)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _secret_cipher():
    """Fernet cipher derived from PYROGUARD_SECRET, or None if unset.

    Any non-empty secret works: raw 44-char Fernet keys are used as-is,
    anything else is stretched with SHA-256 into a valid Fernet key.
    """
    import base64
    raw = os.getenv("PYROGUARD_SECRET", "")
    if not raw:
        return None
    try:
        from cryptography.fernet import Fernet
        key = raw.encode()
        try:
            return Fernet(key if len(key) == 44 else base64.urlsafe_b64encode(__import__("hashlib").sha256(key).digest()))
        except Exception:
            return Fernet(base64.urlsafe_b64encode(__import__("hashlib").sha256(key).digest()))
    except ImportError:
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a secret for DB storage. Falls back to plaintext + warning."""
    cipher = _secret_cipher()
    if cipher is None:
        import logging
        logging.getLogger(__name__).warning("PYROGUARD_SECRET not set; storing secret in plaintext")
        return plaintext
    return "enc:" + cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(stored: Optional[str]) -> Optional[str]:
    """Decrypt a value produced by encrypt_value. Returns None on failure."""
    if not stored:
        return None
    if not stored.startswith("enc:"):
        return stored  # legacy/plaintext value
    cipher = _secret_cipher()
    if cipher is None:
        return None
    try:
        return cipher.decrypt(stored[4:].encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature for webhook payloads."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


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