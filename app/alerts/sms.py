"""SMS alert providers (Twilio + generic webhook)."""
from typing import Optional
import httpx

from app.alerts import AlertProvider, AlertResult, register_provider


class TwilioSMSProvider(AlertProvider):
    """Twilio SMS alert provider."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.account_sid = config.get("account_sid")
        self.auth_token = config.get("auth_token")
        self.from_number = config.get("from_number")
        self.to_number = config.get("to")

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, "sms", self.to_number, "Provider disabled")

        if not all([self.account_sid, self.auth_token, self.from_number, self.to_number]):
            return AlertResult(False, "sms", self.to_number, "Incomplete Twilio config")

        subject, message = self._build_message(incident_data)

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)

            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number,
            )

            return AlertResult(True, "sms", self.to_number)
        except Exception as e:
            return AlertResult(False, "sms", self.to_number, f"Twilio error: {e}")


class WebhookSMSProvider(AlertProvider):
    """Generic webhook SMS provider (for custom SMS gateways)."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url")
        self.webhook_secret = config.get("webhook_secret")
        self.to_number = config.get("to")

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, "sms_webhook", self.to_number, "Provider disabled")

        if not self.webhook_url:
            return AlertResult(False, "sms_webhook", self.to_number, "Webhook URL not configured")

        subject, message = self._build_message(incident_data)

        payload = {
            "to": self.to_number,
            "subject": subject,
            "message": message,
            "incident": incident_data,
        }

        headers = {"Content-Type": "application/json"}
        if self.webhook_secret:
            import hmac
            import hashlib
            body = str(payload).encode()
            sig = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Signature"] = f"sha256={sig}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json=payload, headers=headers)
                resp.raise_for_status()
                return AlertResult(True, "sms_webhook", self.to_number)
        except httpx.HTTPError as e:
            return AlertResult(False, "sms_webhook", self.to_number, f"Webhook error: {e}")
        except Exception as e:
            return AlertResult(False, "sms_webhook", self.to_number, f"Unexpected error: {e}")


def _get_sms_provider(config: dict) -> Optional[AlertProvider]:
    """Factory to get the appropriate SMS provider based on config."""
    provider_type = config.get("provider", "twilio").lower()
    if provider_type == "twilio":
        return TwilioSMSProvider(config)
    elif provider_type == "webhook":
        return WebhookSMSProvider(config)
    return None


# Register providers dynamically based on config
# (Done in get_providers in base.py)