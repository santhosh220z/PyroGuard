"""Telegram bot alert provider."""
import asyncio
from typing import Optional

import httpx

from app.alerts import AlertProvider, AlertResult, register_provider


class TelegramProvider(AlertProvider):
    """Telegram bot alert provider using Bot API."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.bot_token = config.get("bot_token")
        self.chat_id = config.get("chat_id")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, "telegram", self.chat_id, "Provider disabled")

        if not self.bot_token or not self.chat_id:
            return AlertResult(False, "telegram", self.chat_id, "Incomplete Telegram config")

        subject, message = self._build_message(incident_data)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Send photo with caption if image provided
                if image_bytes:
                    files = {"photo": ("detection.jpg", image_bytes, "image/jpeg")}
                    data = {
                        "chat_id": self.chat_id,
                        "caption": message,
                        "parse_mode": "HTML",
                    }
                    response = await client.post(
                        f"{self.base_url}/sendPhoto",
                        data=data,
                        files=files,
                    )
                else:
                    data = {
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                    }
                    response = await client.post(
                        f"{self.base_url}/sendMessage",
                        json=data,
                    )

                response.raise_for_status()
                result = response.json()
                
                if not result.get("ok"):
                    return AlertResult(
                        False,
                        "telegram",
                        self.chat_id,
                        f"Telegram API error: {result.get('description')}",
                    )

            return AlertResult(True, "telegram", self.chat_id)

        except httpx.HTTPStatusError as e:
            return AlertResult(False, "telegram", self.chat_id, f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            return AlertResult(False, "telegram", self.chat_id, f"Request failed: {e}")
        except Exception as e:
            return AlertResult(False, "telegram", self.chat_id, f"Unexpected error: {e}")

    def _build_message(self, incident_data: dict) -> tuple[str, str]:
        """Build Telegram-formatted message."""
        severity = incident_data.get("severity", "unknown").upper()
        camera = incident_data.get("camera_name", incident_data.get("camera_id", "unknown"))
        confidence = incident_data.get("confidence", 0)
        class_name = incident_data.get("class_name", "unknown")
        detected_at = incident_data.get("detected_at", "unknown")
        incident_id = incident_data.get("id", "pending")

        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")

        message = (
            f"{emoji} <b>PyroGuard Alert: {severity} {class_name.capitalize()}</b>\n\n"
            f"📷 <b>Camera:</b> {camera}\n"
            f"🔥 <b>Type:</b> {class_name.capitalize()}\n"
            f"⚠️ <b>Severity:</b> {severity}\n"
            f"📊 <b>Confidence:</b> {confidence:.1%}\n"
            f"🕐 <b>Detected:</b> {detected_at}\n"
            f"🆔 <b>Incident ID:</b> {incident_id}"
        )
        
        subject = f"PyroGuard: {severity} {class_name.capitalize()}"
        return subject, message


register_provider("telegram", TelegramProvider)