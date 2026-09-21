"""Alert-contact profile API: no login, single profile per deployment.

GET  /api/profile  -> current contacts (for the Profile page)
PUT  /api/profile  -> save contacts; gated by PIN once a PIN is set
"""
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.config.security import rate_limit
from app.config.security import get_password_hash, verify_password
from app.config.security import encrypt_value, decrypt_value
from app.alerts.resend import ResendEmailProvider
from app.database import get_db, get_alert_profile, save_alert_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-().]{5,20}$")


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    notify_email: bool = True
    phone: Optional[str] = None
    notify_sms: bool = False
    telegram_chat_id: Optional[str] = None
    notify_telegram: bool = False
    resend_api_key: Optional[str] = None   # new key to store; null/empty keeps existing
    resend_from: Optional[str] = None      # verified sender (e.g. alerts@yourdomain.com)
    pin: Optional[str] = None       # current PIN (required once a PIN is set)
    new_pin: Optional[str] = None   # set / change PIN (min 4 chars)

    @field_validator("display_name")
    @classmethod
    def _name(cls, v):
        if v is not None and len(v) > 128:
            raise ValueError("Name too long (max 128)")
        return (v or "").strip() or None

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = (v or "").strip() or None
        if v is not None:
            if len(v) > 256 or not _EMAIL_RE.match(v):
                raise ValueError("Invalid email address")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        v = (v or "").strip() or None
        if v is not None:
            digits = re.sub(r"\D", "", v)
            if not (7 <= len(digits) <= 16) or not _PHONE_RE.match(v):
                raise ValueError("Invalid phone number (use E.164, e.g. +15551234567)")
        return v

    @field_validator("telegram_chat_id")
    @classmethod
    def _tg(cls, v):
        v = (v or "").strip() or None
        if v is not None and len(v) > 64:
            raise ValueError("Telegram chat ID too long (max 64)")
        return v

    @field_validator("resend_from")
    @classmethod
    def _resend_from(cls, v):
        v = (v or "").strip() or None
        if v is not None:
            if len(v) > 256 or not _EMAIL_RE.match(v):
                raise ValueError("Invalid verified sender email address")
        return v

    @field_validator("resend_api_key")
    @classmethod
    def _resend_key(cls, v):
        v = (v or "").strip() or None
        if v is not None and len(v) > 128:
            raise ValueError("Resend API key too long (max 128)")
        return v

    @field_validator("new_pin")
    @classmethod
    def _new_pin(cls, v):
        if v is not None and len(v) < 4:
            raise ValueError("PIN must be at least 4 characters")
        return v


def _shape(profile) -> dict:
    if profile is None:
        return {
            "configured": False,
            "display_name": None,
            "email": None,
            "notify_email": True,
            "phone": None,
            "notify_sms": False,
            "telegram_chat_id": None,
            "notify_telegram": False,
            "resend_configured": False,
            "resend_from": None,
            "has_pin": False,
            "updated_at": None,
        }
    return {
        "configured": True,
        "display_name": profile.display_name,
        "email": profile.email,
        "notify_email": profile.notify_email,
        "phone": profile.phone,
        "notify_sms": profile.notify_sms,
        "telegram_chat_id": profile.telegram_chat_id,
        "notify_telegram": profile.notify_telegram,
        "resend_configured": bool(profile.resend_api_key_hash and profile.resend_from),
        "resend_from": profile.resend_from,
        "has_pin": bool(profile.pin_hash),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("", summary="Get alert-contact profile")
@rate_limit("60/minute")
async def read_profile(request: Request, db=Depends(get_db)):
    """Return the current alert-contact profile (no auth)."""
    return _shape(get_alert_profile(db))


@router.put("", summary="Save alert-contact profile")
@rate_limit("10/minute")
async def write_profile(request: Request, body: ProfileUpdate, db=Depends(get_db)):
    """Create/update the alert-contact profile.

    Once a PIN is set, the current PIN must be supplied to save changes.
    """
    existing = get_alert_profile(db)
    if existing is not None and existing.pin_hash:
        if not body.pin or not verify_password(body.pin, existing.pin_hash):
            raise HTTPException(status_code=403, detail="Invalid PIN")

    pin_hash = existing.pin_hash if existing else None
    if body.new_pin:
        pin_hash = get_password_hash(body.new_pin)

    # Resend credentials: a new non-empty key is encrypted at rest and stored.
    # An empty/None key leaves any existing key untouched.
    resend_api_key_enc = None
    if body.resend_api_key is not None and body.resend_api_key:
        if not body.resend_api_key.startswith("re_"):
            raise HTTPException(status_code=400, detail="Invalid Resend API key (should start with 're_')")
        resend_api_key_enc = encrypt_value(body.resend_api_key)

    profile = save_alert_profile(
        db,
        display_name=body.display_name,
        email=body.email,
        notify_email=body.notify_email,
        phone=body.phone,
        notify_sms=body.notify_sms,
        telegram_chat_id=body.telegram_chat_id,
        notify_telegram=body.notify_telegram,
        pin_hash=pin_hash,
        resend_api_key_enc=resend_api_key_enc,
        resend_from=body.resend_from,
    )
    db.commit()
    return _shape(profile)


class ResendTestRequest(BaseModel):
    pin: Optional[str] = None  # current PIN (required once a PIN is set)


@router.post("/resend/test", summary="Send a test email via Resend")
@rate_limit("5/minute")
async def test_resend(request: Request, body: ResendTestRequest, db=Depends(get_db)):
    """Send a real test email through Resend using the saved profile config.

    This intentionally sends a real message - it is the verification step for
    the Resend setup. Automatic fire-detection alerts still respect DRY_RUN.
    """
    existing = get_alert_profile(db)
    if existing is None:
        raise HTTPException(status_code=400, detail="No profile saved yet")

    if existing.pin_hash:
        if not body.pin or not verify_password(body.pin, existing.pin_hash):
            raise HTTPException(status_code=403, detail="Invalid PIN")

    api_key = decrypt_value(existing.resend_api_key_hash)
    if not api_key or not existing.resend_from or not existing.email:
        raise HTTPException(
            status_code=400,
            detail="Resend is not fully configured (need API key, verified sender, and an alert email)",
        )

    provider = ResendEmailProvider({
        "enabled": True,
        "api_key": api_key,
        "from": existing.resend_from,
        "to": existing.email,
    })

    test_incident = {
        "id": "test",
        "camera_id": "camera_01",
        "camera_name": "Test Camera",
        "confidence": 0.85,
        "class_name": "fire",
        "severity": "high",
        "detected_at": datetime.utcnow().isoformat(),
    }

    result = await provider.send(test_incident)
    return {
        "success": result.success,
        "provider": result.provider,
        "recipient": result.recipient,
        "error": result.error,
    }
