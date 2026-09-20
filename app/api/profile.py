"""Alert-contact profile API: no login, single profile per deployment.

GET  /api/profile  -> current contacts (for the Profile page)
PUT  /api/profile  -> save contacts; gated by PIN once a PIN is set
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.config.security import rate_limit
from app.config.security import get_password_hash, verify_password
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
    )
    db.commit()
    return _shape(profile)
