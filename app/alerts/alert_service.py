# PyroGuard Alerts Module
# Alert automation for confirmed fires

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class AlertService:
    """Service for sending alerts when fire is confirmed."""
    
    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        self.cooldown_period = int(os.getenv("ALERT_COOLDOWN", "30"))
        self.last_alert_time = 0
        
        # Alert providers
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
    
    async def send_alert(self, incident_id: str, detection_data: dict):
        """Send alert for confirmed fire."""
        if self.dry_run:
            # Log simulated alert
            print(f"[DRY RUN] Alert would be sent for incident {incident_id}")
            print(f"  Detection: {detection_data.get('class')} at {detection_data.get('confidence', 0):.2f} confidence")
            return True
        
        # Try each alert provider
        success = False
        
        # SMTP alert
        if self.smtp_host and self.smtp_username:
            try:
                success = await self._send_smtp_alert(incident_id, detection_data)
                if success:
                    print(f"SMTP alert sent for incident {incident_id}")
            except Exception as e:
                print(f"SMTP alert failed: {e}")
        
        # Telegram alert
        if self.telegram_bot_token and self.telegram_chat_id:
            try:
                success = await self._send_telegram_alert(incident_id, detection_data)
                if success:
                    print(f"Telegram alert sent for incident {incident_id}")
            except Exception as e:
                print(f"Telegram alert failed: {e}")
        
        # Webhook alert
        if self.webhook_url:
            try:
                success = await self._send_webhook_alert(incident_id, detection_data)
                if success:
                    print(f"Webhook alert sent for incident {incident_id}")
            except Exception as e:
                print(f"Webhook alert failed: {e}")
        
        return success or self.dry_run
    
    async def _send_smtp_alert(self, incident_id: str, detection_data: dict):
        """Send alert via SMTP email."""
        # Implementation would use smtplib
        return False
    
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