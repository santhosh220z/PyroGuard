# PyroGuard Configuration Module
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    # Model settings
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/fire_smoke_yolo.pt")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
    IOU_THRESHOLD: float = float(os.getenv("IOU_THRESHOLD", "0.45"))
    
    # Detection settings
    CONFIRMATION_FRAMES: int = int(os.getenv("CONFIRMATION_FRAMES", "3"))
    CONFIRMATION_WINDOW: int = int(os.getenv("CONFIRMATION_WINDOW", "5"))
    ALERT_COOLDOWN: int = int(os.getenv("ALERT_COOLDOWN", "30"))
    
    # Camera settings
    CAMERA_SOURCE: int = int(os.getenv("CAMERA_SOURCE", "0"))
    IMAGE_SIZE: int = int(os.getenv("IMAGE_SIZE", "640"))
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/incidents/incidents.db")
    
    # Alert settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Mode
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"


# Singleton instance
settings = Settings()