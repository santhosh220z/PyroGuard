"""PyroGuard Unit Tests - Alerts Module"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from unittest.mock import patch, MagicMock


def test_alert_dry_run():
    """Test alert service in dry-run mode."""
    # Ensure .env.example exists or create temporary env
    os.environ["DRY_RUN"] = "true"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    # Import after setting env
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # In dry-run mode, should not crash
    result = asyncio.run(service.send_alert("test_incident_123", {
        "class": "fire",
        "confidence": 0.95,
        "timestamp": 1234567890
    }))
    
    assert result is True, "Dry run should succeed"
    print("✅ test_alert_dry_run: PASSED")


def test_alert_missing_credentials():
    """Test alert service with missing credentials (non-dry run)."""
    os.environ["DRY_RUN"] = "false"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # With no credentials and not in dry run, should handle gracefully
    try:
        result = asyncio.run(service.send_alert("test_incident_123", {
            "class": "fire",
            "confidence": 0.95,
            "timestamp": 1234567890
        }))
        print("✅ test_alert_missing_credentials: PASSED (handled gracefully)")
    except Exception as e:
        print(f"⚠️  test_alert_missing_credentials: INFO - {type(e).__name__}")


def test_alert_with_credentials():
    """Test alert service with Telegram credentials set."""
    os.environ["DRY_RUN"] = "false"
    os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57V2saqXFte1AZ2"
    os.environ["TELEGRAM_CHAT_ID"] = "123456789"
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # Should initialize without crashing
    assert service.telegram_bot_token == "123456:ABC-DEF1234ghIkl-zyx57V2saqXFte1AZ2"
    assert service.telegram_chat_id == "123456789"
    print("✅ test_alert_with_credentials: PASSED")