# PyroGuard Alerts Module
# Alert automation for confirmed fires with deduplication and circuit breaker

import asyncio
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
import dotenv
dotenv.load_dotenv(dotenv_path=env_path)


class AlertService:
    """Service for sending alerts when fire is confirmed."""
    
    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        self.cooldown_period = int(os.getenv("ALERT_COOLDOWN", "30"))
        self.circuit_breaker_failure_threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
        self.circuit_breaker_reset_timeout = int(os.getenv("CIRCUIT_RESET_TIMEOUT", "60"))
        
        # Alert deduplication - prevent duplicate alerts within cooldown
        self.last_alert_incident_ids = deque(maxlen=50)
        self.last_alert_timestamps = {}
        
        # Circuit breaker state per provider
        self.circuit_breakers = {
            "smtp": {"failures": 0, "state": "CLOSED", "last_failure": 0},
            "telegram": {"failures": 0, "state": "CLOSED", "last_failure": 0},
            "webhook": {"failures": 0, "state": "CLOSED", "last_failure": 0},
        }
        
        # Alert providers
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
    
    def should_send_alert(self, incident_id: str) -> bool:
        """
        Check if an alert should be sent for this incident.
        
        Returns True if alert should be sent, False if it's a duplicate within cooldown.
        """
        # In dry run mode, always allow
        if self.dry_run:
            return True
        
        # Check if this incident already had an alert recently
        if incident_id in self.last_alert_incident_ids:
            # Check how long ago the last alert was for this incident
            if incident_id in self.last_alert_timestamps:
                last_time = self.last_alert_timestamps[incident_id]
                elapsed = (datetime.now() - last_time).total_seconds()
                
                if elapsed < self.cooldown_period:
                    # Still within cooldown - don't send duplicate
                    return False
        
        return True
    
    def record_alert_success(self, provider: str):
        """Record a successful alert to reset circuit breaker."""
        if provider in self.circuit_breakers:
            self.circuit_breakers[provider]["failures"] = 0
            if self.circuit_breakers[provider]["state"] == "OPEN":
                self.circuit_breakers[provider]["state"] = "CLOSED"
                print(f"Circuit breaker {provider} closed - service recovered")
    
    def record_alert_failure(self, provider: str):
        """Record an alert failure and potentially open circuit breaker."""
        if provider in self.circuit_breakers:
            cb = self.circuit_breakers[provider]
            cb["failures"] += 1
            
            if cb["failures"] >= self.circuit_breaker_failure_threshold:
                cb["state"] = "OPEN"
                cb["last_failure"] = time.time()
                print(f"Circuit breaker {provider} opened - too many failures")
    
    def can_send_to(self, provider: str) -> bool:
        """Check if a provider is available (circuit breaker closed)."""
        if provider not in self.circuit_breakers:
            return True
        
        cb = self.circuit_breakers[provider]
        
        if cb["state"] == "CLOSED":
            return True
        
        # Check if reset timeout has elapsed
        if cb["state"] == "OPEN" and (time.time() - cb["last_failure"]) > self.circuit_breaker_reset_timeout:
            cb["state"] = "HALF_OPEN"
            print(f"Circuit breaker {provider} moving to HALF_OPEN")
            return True
        
        return False
    
    async def send_alert(self, incident_id: str, detection_data: dict):
        """Send alert for confirmed fire."""
        if not self.should_send_alert(incident_id):
            print(f"[DEDUP] Alert suppressed for incident {incident_id} - within cooldown period")
            return False
        
        # Collect available providers
        providers_to_try = []
        
        # SMTP
        if self.smtp_host and self.smtp_username and self.can_send_to("smtp"):
            providers_to_try.append("smtp")
        
        # Telegram
        if self.telegram_bot_token and self.telegram_chat_id and self.can_send_to("telegram"):
            providers_to_try.append("telegram")
        
        # Webhook
        if self.webhook_url and self.can_send_to("webhook"):
            providers_to_try.append("webhook")
        
        if not providers_to_try:
            print("[CIRCUIT] No alert providers available")
            return self.dry_run
        
        if self.dry_run:
            # Log simulated alert
            print(f"[DRY RUN] Alert would be sent for incident {incident_id}")
            print(f"  Detection: {detection_data.get('class')} at {detection_data.get('confidence', 0):.2f} confidence")
            # Record success for all providers in dry run
            for p in providers_to_try:
                self.record_alert_success(p)
            return True
        
        # Record start time for timing
        start_time = time.time()
        
        # Try each available provider
        success_count = 0
        
        for provider in providers_to_try:
            try:
                if provider == "smtp":
                    success = await self._send_smtp_alert(incident_id, detection_data)
                elif provider == "telegram":
                    success = await self._send_telegram_alert(incident_id, detection_data)
                elif provider == "webhook":
                    success = await self._send_webhook_alert(incident_id, detection_data)
                else:
                    success = False
                
                if success:
                    success_count += 1
                    self.record_alert_success(provider)
                    print(f"{provider.upper()} alert sent for incident {incident_id}")
                else:
                    self.record_alert_failure(provider)
                    print(f"{provider.upper()} alert failed for incident {incident_id}")
            except Exception as e:
                self.record_alert_failure(provider)
                print(f"{provider.upper()} alert exception for incident {incident_id}: {e}")
        
        elapsed = time.time() - start_time
        print(f"Alert processing completed in {elapsed:.2f}s, {success_count}/{len(providers_to_try)} successful")
        
        return success_count > 0
    
    async def _send_smtp_alert(self, incident_id: str, detection_data: dict):
        """Send alert via SMTP email."""
        # Implementation would use smtplib
        import aiohttp
        # Simulate email sending
        await asyncio.sleep(0.1)
        # Return True to simulate success, False for failure
        return True
    
    async def _send_telegram_alert(self, incident_id: str, detection_data: dict):
        """Send alert via Telegram."""
        import aiohttp
        message = f"🔥 Fire detected!\nIncident ID: {incident_id}\nClass: {detection_data.get('class')}\nConfidence: {detection_data.get('confidence', 0):.2f}"
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                data={"chat_id": self.telegram_chat_id, "text": message}
            )
    
    async def _send_webhook_alert(self, incident_id: str, detection_data: dict):
        """Send alert via webhook."""
        import aiohttp
        payload = {
            "incident_id": incident_id,
            "class": detection_data.get("class"),
            "confidence": detection_data.get("confidence"),
            "timestamp": detection_data.get("timestamp")
        }
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=payload)