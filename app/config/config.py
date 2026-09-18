# PyroGuard Configuration Module
# Loads YAML config with .env overrides (env vars take precedence)

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Load .env file (secrets + overrides)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Project root for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load YAML config as base defaults
_yaml_settings = {}
_config_yaml = PROJECT_ROOT / "configs" / "config.yaml"
try:
    import yaml
    if _config_yaml.exists():
        with open(_config_yaml, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                _yaml_settings = loaded
except ImportError:
    pass  # PyYAML not installed; fall back to env/code defaults only


def _setting(key: str, default, cast=None):
    """Resolve a setting: env var overrides YAML overrides code default."""
    value = os.getenv(key, _yaml_settings.get(key, default))
    if cast is not None and not isinstance(value, bool):
        try:
            return cast(value)
        except (TypeError, ValueError):
            return default
    return value


def _parse_cameras(raw: Any) -> List[Dict[str, Any]]:
    """Parse CAMERAS from YAML (list of dicts) or env (JSON string)."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            import json
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    return []


class Settings:
    """Application settings loaded from YAML + environment variables."""

    def __init__(self):
        # Model settings
        self.MODEL_PATH: str = _setting("MODEL_PATH", "models/fire_smoke_yolo.pt", str)
        self.CONFIDENCE_THRESHOLD: float = _setting("CONFIDENCE_THRESHOLD", 0.25, float)
        self.IOU_THRESHOLD: float = _setting("IOU_THRESHOLD", 0.45, float)
        self.IMAGE_SIZE: int = _setting("IMAGE_SIZE", 640, int)

        # Detection / temporal verification
        self.CONFIRMATION_FRAMES: int = _setting("CONFIRMATION_FRAMES", 3, int)
        self.CONFIRMATION_WINDOW: int = _setting("CONFIRMATION_WINDOW", 5, int)

        # Camera
        self.CAMERA_SOURCE: str = _setting("CAMERA_SOURCE", "0", str)
        self.CAMERAS: List[Dict[str, Any]] = _parse_cameras(_setting("CAMERAS", [], list))

        # Database
        self.DATABASE_URL: str = _setting("DATABASE_URL", "sqlite:///data/incidents/incidents.db", str)

        # Alert settings (deferred; automations come later)
        self.SMTP_HOST: str = _setting("SMTP_HOST", "", str)
        self.SMTP_PORT: int = _setting("SMTP_PORT", 587, int)
        self.SMTP_USERNAME: str = _setting("SMTP_USERNAME", "", str)
        # SMTP_PASSWORD loaded from env only (never from YAML)
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM: str = _setting("SMTP_FROM", "", str)
        self.SMTP_TO: str = _setting("SMTP_TO", "", str)

        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID: str = _setting("TELEGRAM_CHAT_ID", "", str)

        self.WEBHOOK_URL: str = _setting("WEBHOOK_URL", "", str)
        # WEBHOOK_SECRET loaded from env only
        self.WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

        # Alert cooldown
        self.ALERT_COOLDOWN: int = _setting("ALERT_COOLDOWN", 30, int)

        # Authentication
        self.JWT_SECRET: str = os.getenv("JWT_SECRET", "")
        self.API_KEYS: str = os.getenv("API_KEYS", "")

        # CORS
        self.ALLOWED_ORIGINS: str = _setting("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000", str)

        # Logging
        self.LOG_LEVEL: str = _setting("LOG_LEVEL", "INFO", str)

        # Mode
        self.DRY_RUN: bool = str(_setting("DRY_RUN", "true", str)).lower() == "true"

        # Validate on init
        self._validate()

    def _validate(self):
        """Validate critical settings and warn on issues."""
        import logging
        logger = logging.getLogger(__name__)

        # Model file existence
        model_path = PROJECT_ROOT / self.MODEL_PATH
        if not model_path.exists():
            logger.warning(f"Model file not found: {model_path}")

        # Database directory
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_path = self.DATABASE_URL.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Alert validation (only if not DRY_RUN)
        if not self.DRY_RUN:
            if self.SMTP_HOST and not self.SMTP_PASSWORD:
                logger.warning("SMTP_HOST set but SMTP_PASSWORD missing (set in .env)")
            if self.TELEGRAM_BOT_TOKEN and not self.TELEGRAM_CHAT_ID:
                logger.warning("TELEGRAM_BOT_TOKEN set but TELEGRAM_CHAT_ID missing")
            if self.WEBHOOK_URL and not self.WEBHOOK_SECRET:
                logger.warning("WEBHOOK_URL set but WEBHOOK_SECRET missing (set in .env)")

        # Auth validation
        if not self.JWT_SECRET and not self.DRY_RUN:
            logger.warning("JWT_SECRET not set; using generated secret (tokens invalid on restart)")

    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert provider configs as a dict."""
        return {
            "email": {
                "enabled": bool(self.SMTP_HOST and self.SMTP_PASSWORD and self.SMTP_TO),
                "host": self.SMTP_HOST,
                "port": self.SMTP_PORT,
                "username": self.SMTP_USERNAME,
                "password": self.SMTP_PASSWORD,
                "from_addr": self.SMTP_FROM or self.SMTP_USERNAME,
                "to_addr": self.SMTP_TO,
            },
            "telegram": {
                "enabled": bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID),
                "bot_token": self.TELEGRAM_BOT_TOKEN,
                "chat_id": self.TELEGRAM_CHAT_ID,
            },
            "webhook": {
                "enabled": bool(self.WEBHOOK_URL and self.WEBHOOK_SECRET),
                "url": self.WEBHOOK_URL,
                "secret": self.WEBHOOK_SECRET,
            },
        }


# Singleton instance
settings = Settings()