"""Generic webhook alert provider with HMAC signature."""
import json
import time
import hmac
import hashlib
from typing import Optional

import httpx

from app.alerts import AlertProvider, AlertResult, register_provider
from app.config.security import verify_webhook_signature


class WebhookProvider(AlertProvider):
    """Generic HTTP webhook alert provider with HMAC-SHA256 signing."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.url = config.get("url")
        self.secret = config.get("secret")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 10)

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, "webhook", self.url, "Provider disabled")

        if not self.url or not self.secret:
            return AlertResult(False, "webhook", self.url, "Incomplete webhook config (url/secret)")

        # Build payload
        payload = {
            "event": "fire_smoke_detected",
            "timestamp": time.time(),
            "incident": {
                "id": incident_data.get("id"),
                "camera_id": incident_data.get("camera_id"),
                "camera_name": incident_data.get("camera_name"),
                "class_name": incident_data.get("class_name"),
                "confidence": incident_data.get("confidence"),
                "severity": incident_data.get("severity"),
                "bbox": {
                    "x1": incident_data.get("bbox_x1"),
                    "y1": incident_data.get("bbox_y1"),
                    "x2": incident_data.get("bbox_x2"),
                    "y2": incident_data.get("bbox_y2"),
                },
                "detected_at": incident_data.get("detected_at"),
                "snapshot_path": incident_data.get("snapshot_path"),
            },
        }

        # Add image as base64 if provided
        if image_bytes:
            import base64
            payload["incident"]["image_base64"] = base64.b64encode(image_bytes).decode()

        body = json.dumps(payload, separators=(",", ":")).encode()
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={signature}"

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-PyroGuard-Signature": signature_header,
            "X-PyroGuard-Timestamp": str(int(time.time())),
            "User-Agent": "PyroGuard/1.0",
        }
        headers.update(self.headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, content=body, headers=headers)
                response.raise_for_status()

            return AlertResult(True, "webhook", self.url)

        except httpx.HTTPStatusError as e:
            return AlertResult(False, "webhook", self.url, f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            return AlertResult(False, "webhook", self.url, f"Request failed: {e}")
        except Exception as e:
            return AlertResult(False, "webhook", self.url, f"Unexpected error: {e}")


def verify_webhook_request(payload: bytes, signature_header: str, secret: str) -> bool:
    """Verify incoming webhook request signature (for webhook receivers)."""
    return verify_webhook_signature(payload, signature_header, secret)


register_provider("webhook", WebhookProvider)