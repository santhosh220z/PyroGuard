# PyroGuard Configuration Module
# Loads YAML config with .env overrides (env vars take precedence)

import os
from pathlib import Path

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
        self.CAMERAS: list = _setting("CAMERAS", [], list)

        # Logging
        self.LOG_LEVEL: str = _setting("LOG_LEVEL", "INFO", str)

        # Mode
        self.DRY_RUN: bool = str(_setting("DRY_RUN", "true", str)).lower() == "true"


# Singleton instance
settings = Settings()