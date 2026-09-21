"""Resend email alert provider (https://resend.com API)."""
import base64
from typing import Optional

import httpx

from app.alerts import AlertProvider, AlertResult, register_provider


class ResendEmailProvider(AlertProvider):
    """Email alerts delivered through the Resend API.

    Config keys: api_key, from (verified sender), to (recipient), enabled,
    and optionally image (base64-encoded default attachment).
    """

    PROVIDER_NAME = "resend"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.from_addr = config.get("from")
        self.to_addr = config.get("to")
        self.image = config.get("image")

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, self.PROVIDER_NAME, self.to_addr, "Provider disabled")

        if not all([self.api_key, self.from_addr, self.to_addr]):
            return AlertResult(False, self.PROVIDER_NAME, self.to_addr, "Incomplete Resend config")

        subject, message = self._build_message(incident_data)
        html = self._build_html(incident_data, image_bytes)

        payload = {
            "from": self.from_addr,
            "to": self.to_addr,
            "subject": subject,
            "html": html,
        }

        # Attach detection image as base64 when available.
        attachment_content = self._attachment_content(image_bytes)
        if attachment_content:
            payload["attachments"] = [
                {"filename": "detection.jpg", "content": attachment_content}
            ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

            return AlertResult(True, self.PROVIDER_NAME, self.to_addr)

        except httpx.HTTPStatusError as e:
            return AlertResult(
                False,
                self.PROVIDER_NAME,
                self.to_addr,
                f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except httpx.RequestError as e:
            return AlertResult(False, self.PROVIDER_NAME, self.to_addr, f"Request failed: {e}")
        except Exception as e:
            return AlertResult(False, self.PROVIDER_NAME, self.to_addr, f"Unexpected error: {e}")

    def _attachment_content(self, image_bytes: Optional[bytes]) -> Optional[str]:
        """Return base64 attachment content for the image, or None.

        Prefers the runtime incident image bytes; falls back to the
        configured ``image`` value (already base64 or raw bytes).
        """
        if image_bytes is not None:
            return base64.b64encode(image_bytes).decode("ascii")
        if isinstance(self.image, str) and self.image:
            return self.image
        if isinstance(self.image, (bytes, bytearray)) and self.image:
            return base64.b64encode(self.image).decode("ascii")
        return None

    def _build_html(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> str:
        """Build the HTML body for the Resend email."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #dc2626;">\U0001F525 PyroGuard Fire &amp; Smoke Alert</h2>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                <tr><td style="padding: 8px;"><strong>Camera:</strong></td><td style="padding: 8px;">{incident_data.get('camera_name', incident_data.get('camera_id', 'unknown'))}</td></tr>
                <tr><td style="padding: 8px;"><strong>Type:</strong></td><td style="padding: 8px;">{incident_data.get('class_name', 'unknown').capitalize()}</td></tr>
                <tr><td style="padding: 8px;"><strong>Severity:</strong></td><td style="padding: 8px;"><span style="color: {self._severity_color(incident_data.get('severity'))}; font-weight: bold;">{incident_data.get('severity', 'unknown').upper()}</span></td></tr>
                <tr><td style="padding: 8px;"><strong>Confidence:</strong></td><td style="padding: 8px;">{incident_data.get('confidence', 0):.1%}</td></tr>
                <tr><td style="padding: 8px;"><strong>Detected:</strong></td><td style="padding: 8px;">{incident_data.get('detected_at', 'unknown')}</td></tr>
                <tr><td style="padding: 8px;"><strong>Incident ID:</strong></td><td style="padding: 8px;">{incident_data.get('id', 'pending')}</td></tr>
            </table>
            {"<p><img src='cid:detection_image' style='max-width: 100%; border-radius: 8px;'></p>" if image_bytes else ""}
            <hr>
            <p style="color: #666; font-size: 12px;">This is an automated alert from PyroGuard. Do not reply.</p>
        </body>
        </html>
        """

    def _severity_color(self, severity: str) -> str:
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#16a34a",
        }
        return colors.get((severity or "").lower(), "#666")


register_provider("resend", ResendEmailProvider)