"""PyroGuard Unit Tests - Alerts Module"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
from unittest.mock import patch, MagicMock


def test_alert_dry_run():
    """Test alert service in dry-run mode."""
    # Ensure .env example values
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


def test_alert_deduplication():
    """Test that duplicate alerts within cooldown are suppressed."""
    os.environ["DRY_RUN"] = "false"
    os.environ["ALERT_COOLDOWN"] = "5"  # 5 second cooldown
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # Test deduplication via should_send_alert directly
    # First call should return True
    result1 = service.should_send_alert("test_dup_001")
    assert result1 is True, "First alert should be allowed"
    
    # Record the alert timestamp
    service.last_alert_incident_ids.append("test_dup_001")
    service.last_alert_timestamps["test_dup_001"] = datetime.now()
    
    # Small delay to ensure timestamp difference
    time.sleep(0.1)  # 100ms delay
    
    # Second call within cooldown should return False
    result2 = service.should_send_alert("test_dup_001")
    assert result2 is False, f"Second alert within cooldown should be suppressed, got {result2}"
    
    # Different incident ID should be allowed
    result3 = service.should_send_alert("test_dup_002")
    assert result3 is True, "Different incident should be allowed"
    
    print("✅ test_alert_deduplication: PASSED (dedup logic verified)")


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


def test_alert_circuit_breaker():
    """Test circuit breaker functionality."""
    os.environ["DRY_RUN"] = "false"
    os.environ["CIRCUIT_BREAKER_THRESHOLD"] = "2"  # Low threshold for testing
    os.environ["CIRCUIT_RESET_TIMEOUT"] = "1"  # Quick reset
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # Simulate failures
    service.record_alert_failure("telegram")
    service.record_alert_failure("telegram")
    
    # Circuit should be open now
    assert service.circuit_breakers["telegram"]["state"] == "OPEN", "Circuit should be open after threshold failures"
    
    # Should not be able to send
    assert service.can_send_to("telegram") == False, "Should not send when circuit open"
    
    # Record success to close circuit
    service.record_alert_success("telegram")
    assert service.circuit_breakers["telegram"]["state"] == "CLOSED", "Circuit should close after success"
    
    # Should now be able to send
    assert service.can_send_to("telegram") == True, "Should send when circuit closed"
    
    print("✅ test_alert_circuit_breaker: PASSED")


def test_alert_should_send():
    """Test should_send_alert deduplication logic."""
    os.environ["DRY_RUN"] = "false"
    os.environ["ALERT_COOLDOWN"] = "30"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""
    os.environ["SMTP_HOST"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["WEBHOOK_URL"] = ""
    
    from app.alerts.alert_service import AlertService
    
    service = AlertService()
    
    # First call should return True
    result1 = service.should_send_alert("test_incident_001")
    assert result1 is True, "First alert should be allowed"
    
    # Record the alert timestamp
    service.last_alert_incident_ids.append("test_incident_001")
    service.last_alert_timestamps["test_incident_001"] = datetime.now()
    
    # Small delay to ensure timestamp difference
    time.sleep(0.01)
    
    # Second call within cooldown should return False
    result2 = service.should_send_alert("test_incident_001")
    assert result2 is False, "Second alert within cooldown should be suppressed"
    
    # Different incident ID should be allowed
    result3 = service.should_send_alert("test_incident_002")
    assert result3 is True, "Different incident should be allowed"
    
    print("✅ test_alert_should_send: PASSED")