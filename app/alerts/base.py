"""Base alert provider interface."""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class AlertResult:
    """Result of an alert send attempt."""
    success: bool
    provider: str
    recipient: str
    error: Optional[str] = None


class AlertProvider(ABC):
    """Base class for alert providers."""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        """Send alert for an incident. Returns AlertResult."""
        pass

    def _build_message(self, incident_data: dict) -> tuple[str, str]:
        """Build subject and message from incident data."""
        severity = incident_data.get("severity", "unknown").upper()
        camera = incident_data.get("camera_name", incident_data.get("camera_id", "unknown"))
        confidence = incident_data.get("confidence", 0)
        class_name = incident_data.get("class_name", "unknown")
        detected_at = incident_data.get("detected_at", "unknown")
        
        subject = f"PyroGuard Alert: {severity} {class_name.capitalize()} Detected"
        message = (
            f"PyroGuard Fire & Smoke Detection Alert\n\n"
            f"Camera: {camera}\n"
            f"Type: {class_name.capitalize()}\n"
            f"Severity: {severity}\n"
            f"Confidence: {confidence:.1%}\n"
            f"Detected: {detected_at}\n"
            f"Incident ID: {incident_data.get('id', 'pending')}\n"
        )
        return subject, message


# Provider registry
PROVIDER_REGISTRY = {}


def register_provider(name: str, provider_class):
    """Register an alert provider class."""
    PROVIDER_REGISTRY[name] = provider_class


def get_providers(config: dict) -> list:
    """Get enabled provider instances from config."""
    providers = []
    for name, provider_class in PROVIDER_REGISTRY.items():
        provider_config = config.get(name, {})
        if provider_config.get("enabled"):
            providers.append(provider_class(provider_config))
    return providers