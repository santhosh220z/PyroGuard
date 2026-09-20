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

# Load YAML configs as base defaults
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

# Load alerts config
_alerts_yaml = PROJECT_ROOT / "config" / "alerts.yaml"
_alerts_settings = {}
try:
    import yaml
    if _alerts_yaml.exists():
        with open(_alerts_yaml, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                _alerts_settings = loaded
except ImportError:
    pass


def _setting(key: str, default, cast=None):
    """Resolve a setting: env var overrides YAML overrides code default."""
    value = os.getenv(key, _yaml_settings.get(key, default))
    if cast is not None and not isinstance(value, bool):
        try:
            return cast(value)
        except (TypeError, ValueError):
            return default
    return value


def _alert_setting(path: str, default=None):
    """Resolve an alert setting from alerts.yaml with env override.
    Env var format: ALERT_EMAIL_ENABLED, ALERT_EMAIL_TO, ALERT_TELEGRAM_CHAT_ID, etc.
    """
    # Try env var first (uppercase with ALERT_ prefix)
    env_key = "ALERT_" + path.upper().replace(".", "_")
    if env_key in os.environ:
        return os.environ[env_key]
    # Fall back to YAML
    keys = path.split(".")
    value = _alerts_settings
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
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

        # Alert cooldown
        self.ALERT_COOLDOWN: int = _setting("ALERT_COOLDOWN", 30, int)

        # CORS
        self.ALLOWED_ORIGINS: str = _setting("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000", str)

        # Logging
        self.LOG_LEVEL: str = _setting("LOG_LEVEL", "INFO", str)

        # Mode
        self.DRY_RUN: bool = str(_setting("DRY_RUN", "true", str)).lower() == "true"

        # Alert settings (loaded from alerts.yaml + env overrides)
        self._load_alert_settings()

        # Validate on init
        self._validate()

    def _load_alert_settings(self):
        """Load alert settings from alerts.yaml with env overrides."""
        # Email
        self.ALERT_EMAIL_ENABLED = _alert_setting("email.enabled", False)
        self.ALERT_EMAIL_TO = _alert_setting("email.to", "")
        self.SMTP_HOST = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM = os.getenv("SMTP_FROM", "")
        
        # Telegram
        self.ALERT_TELEGRAM_ENABLED = _alert_setting("telegram.enabled", False)
        self.ALERT_TELEGRAM_CHAT_ID = _alert_setting("telegram.chat_id", "")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Webhook
        self.ALERT_WEBHOOK_ENABLED = _alert_setting("webhook.enabled", False)
        self.ALERT_WEBHOOK_URL = _alert_setting("webhook.url", "")
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
        
        # SMS
        self.ALERT_SMS_ENABLED = _alert_setting("sms.enabled", False)
        self.ALERT_SMS_PROVIDER = _alert_setting("sms.provider", "twilio")
        self.ALERT_SMS_TO = _alert_setting("sms.to", "")
        self.TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.TWILIO_FROM = os.getenv("TWILIO_FROM", "")
        self.SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "")
        self.SMS_WEBHOOK_SECRET = os.getenv("SMS_WEBHOOK_SECRET", "")

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
            if self.ALERT_EMAIL_ENABLED and not (self.SMTP_HOST and self.SMTP_PASSWORD and self.ALERT_EMAIL_TO):
                logger.warning("Email alerts enabled but SMTP config incomplete (check .env and alerts.yaml)")
            if self.ALERT_TELEGRAM_ENABLED and not (self.TELEGRAM_BOT_TOKEN and self.ALERT_TELEGRAM_CHAT_ID):
                logger.warning("Telegram alerts enabled but bot token or chat ID missing")
            if self.ALERT_WEBHOOK_ENABLED and not (self.ALERT_WEBHOOK_URL and self.WEBHOOK_SECRET):
                logger.warning("Webhook alerts enabled but URL or secret missing")

    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert provider configs as a dict (from alerts.yaml + env)."""
        return {
            "email": {
                "enabled": self.ALERT_EMAIL_ENABLED,
                "host": self.SMTP_HOST,
                "port": self.SMTP_PORT,
                "username": self.SMTP_USERNAME,
                "password": self.SMTP_PASSWORD,
                "from_addr": self.SMTP_FROM or self.SMTP_USERNAME,
                "to_addr": self.ALERT_EMAIL_TO,
            },
            "telegram": {
                "enabled": self.ALERT_TELEGRAM_ENABLED,
                "bot_token": self.TELEGRAM_BOT_TOKEN,
                "chat_id": self.ALERT_TELEGRAM_CHAT_ID,
            },
            "webhook": {
                "enabled": self.ALERT_WEBHOOK_ENABLED,
                "url": self.ALERT_WEBHOOK_URL,
                "secret": self.WEBHOOK_SECRET,
            },
            "sms": {
                "enabled": self.ALERT_SMS_ENABLED,
                "provider": self.ALERT_SMS_PROVIDER,
                "to": self.ALERT_SMS_TO,
                "account_sid": self.TWILIO_ACCOUNT_SID,
                "auth_token": self.TWILIO_AUTH_TOKEN,
                "from_number": self.TWILIO_FROM,
                "webhook_url": self.SMS_WEBHOOK_URL,
                "webhook_secret": self.SMS_WEBHOOK_SECRET,
            },
        }


# Singleton instance
settings = Settings()