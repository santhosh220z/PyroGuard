"""Alert providers package."""
from app.alerts.base import AlertProvider, AlertResult, PROVIDER_REGISTRY, register_provider, get_providers
from app.alerts.email import EmailProvider
from app.alerts.telegram import TelegramProvider
from app.alerts.webhook import WebhookProvider, verify_webhook_request
from app.alerts.sms import TwilioSMSProvider, WebhookSMSProvider
from app.alerts.resend import ResendEmailProvider

__all__ = [
    "AlertProvider",
    "AlertResult",
    "PROVIDER_REGISTRY",
    "register_provider",
    "get_providers",
    "EmailProvider",
    "TelegramProvider",
    "WebhookProvider",
    "verify_webhook_request",
    "TwilioSMSProvider",
    "WebhookSMSProvider",
    "ResendEmailProvider",
]