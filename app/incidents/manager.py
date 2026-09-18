"""Incident lifecycle manager: create, acknowledge, resolve, and trigger alerts."""
import asyncio
import os
import shutil
import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.database import (
    create_incident,
    get_incident,
    get_incidents,
    count_incidents,
    acknowledge_incident,
    resolve_incident,
    create_alert,
    update_alert_status,
    get_alerts_for_incident,
    get_audit_logs,
    get_incident_stats,
)
from app.database.database import get_db_session
from app.alerts import get_providers, AlertResult
from app.config.config import settings


@dataclass
class IncidentData:
    """Data needed to create an incident."""
    camera_id: str
    camera_name: str
    confidence: float
    bbox: Dict[str, float]
    class_name: str
    image_bytes: Optional[bytes] = None


class IncidentManager:
    """Manages incident lifecycle and alert dispatching."""

    def __init__(self):
        self.providers = get_providers(settings.get_alert_config())
        self._cooldowns: Dict[str, float] = {}  # camera_id -> last_alert_time
        self._cooldown_lock = threading.Lock()
        self._snapshot_dir = Path("data/incidents/snapshots")
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    def is_in_cooldown(self, camera_id: str) -> bool:
        """Check if camera is in alert cooldown period."""
        with self._cooldown_lock:
            last_alert = self._cooldowns.get(camera_id, 0)
            return (datetime.utcnow().timestamp() - last_alert) < settings.ALERT_COOLDOWN

    def set_cooldown(self, camera_id: str):
        """Set cooldown timestamp for a camera."""
        with self._cooldown_lock:
            self._cooldowns[camera_id] = datetime.utcnow().timestamp()

    def _save_snapshot(self, incident_id: int, image_bytes: bytes) -> Optional[str]:
        """Save incident snapshot to disk."""
        if not image_bytes:
            return None
        try:
            filename = f"incident_{incident_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self._snapshot_dir / filename
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            return str(filepath)
        except Exception:
            return None

    async def _dispatch_alerts(
        self,
        incident_data: Dict[str, Any],
        image_bytes: Optional[bytes],
    ) -> List[AlertResult]:
        """Dispatch alerts to all enabled providers concurrently."""
        if not self.providers:
            return []

        # Prepare tasks
        tasks = [
            provider.send(incident_data, image_bytes)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(AlertResult(
                    False,
                    self.providers[i].name,
                    "unknown",
                    str(result),
                ))
            else:
                processed.append(result)
        return processed

    def _record_alert_results(self, incident_id: int, results: List[AlertResult]):
        """Record alert send results in database."""
        with get_db_session() as db:
            for result in results:
                alert = create_alert(
                    db,
                    incident_id=incident_id,
                    provider=result.provider,
                    recipient=result.recipient,
                    subject=f"PyroGuard Alert: {incident_id}",
                    message=result.error or "Alert sent successfully",
                )
                status = "sent" if result.success else "failed"
                update_alert_status(db, alert.id, status, result.error)

    def create_incident(
        self,
        camera_id: str,
        camera_name: str,
        confidence: float,
        bbox: Dict[str, float],
        class_name: str,
        image_bytes: Optional[bytes] = None,
    ) -> Optional[int]:
        """
        Create a new incident and dispatch alerts.
        Returns incident ID or None if in cooldown.
        """
        # Check cooldown
        if self.is_in_cooldown(camera_id):
            return None

        with get_db_session() as db:
            # Create incident
            incident = create_incident(
                db,
                camera_id=camera_id,
                camera_name=camera_name,
                confidence=confidence,
                bbox=bbox,
                class_name=class_name,
            )
            incident_id = incident.id

            # Save snapshot
            snapshot_path = self._save_snapshot(incident_id, image_bytes)
            if snapshot_path:
                incident.snapshot_path = snapshot_path
                db.flush()

            # Prepare data for alerts
            incident_data = {
                "id": incident_id,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "confidence": confidence,
                "bbox_x1": bbox.get("x1"),
                "bbox_y1": bbox.get("y1"),
                "bbox_x2": bbox.get("x2"),
                "bbox_y2": bbox.get("y2"),
                "class_name": class_name,
                "severity": incident.severity.value,
                "detected_at": incident.detected_at.isoformat(),
                "snapshot_path": snapshot_path,
            }

            # Set cooldown
            self.set_cooldown(camera_id)

            # Dispatch alerts asynchronously
            if not settings.DRY_RUN:
                # Run in background thread to not block detection
                def run_alerts():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        results = loop.run_until_complete(
                            self._dispatch_alerts(incident_data, image_bytes)
                        )
                        self._record_alert_results(incident_id, results)
                    finally:
                        loop.close()

                thread = threading.Thread(target=run_alerts, daemon=True)
                thread.start()
            else:
                # DRY_RUN: just log
                print(f"[DRY_RUN] Would dispatch alerts for incident {incident_id}: {incident_data}")

            return incident_id

    def acknowledge(self, incident_id: int, user: str) -> bool:
        """Acknowledge an incident."""
        with get_db_session() as db:
            incident = acknowledge_incident(db, incident_id, user)
            return incident is not None

    def resolve(self, incident_id: int, user: str, false_positive: bool = False) -> bool:
        """Resolve an incident."""
        with get_db_session() as db:
            incident = resolve_incident(db, incident_id, user, false_positive)
            return incident is not None

    def get_incident(self, incident_id: int) -> Optional[Dict[str, Any]]:
        """Get incident details."""
        with get_db_session() as db:
            incident = get_incident(db, incident_id)
            if not incident:
                return None
            return {
                "id": incident.id,
                "camera_id": incident.camera_id,
                "camera_name": incident.camera_name,
                "confidence": incident.confidence,
                "bbox": {
                    "x1": incident.bbox_x1,
                    "y1": incident.bbox_y1,
                    "x2": incident.bbox_x2,
                    "y2": incident.bbox_y2,
                },
                "class_name": incident.class_name,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
                "acknowledged_at": incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "acknowledged_by": incident.acknowledged_by,
                "resolved_by": incident.resolved_by,
                "snapshot_path": incident.snapshot_path,
            }

    def list_incidents(
        self,
        status: Optional[str] = None,
        camera_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List incidents with filters."""
        from app.database.models import IncidentStatus, IncidentSeverity
        
        status_enum = IncidentStatus(status) if status else None
        severity_enum = IncidentSeverity(severity) if severity else None
        
        with get_db_session() as db:
            incidents = get_incidents(
                db,
                status=status_enum,
                camera_id=camera_id,
                severity=severity_enum,
                limit=limit,
                offset=offset,
            )
            return [
                {
                    "id": inc.id,
                    "camera_id": inc.camera_id,
                    "camera_name": inc.camera_name,
                    "confidence": inc.confidence,
                    "class_name": inc.class_name,
                    "severity": inc.severity.value,
                    "status": inc.status.value,
                    "detected_at": inc.detected_at.isoformat() if inc.detected_at else None,
                    "snapshot_path": inc.snapshot_path,
                }
                for inc in incidents
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Get incident statistics."""
        with get_db_session() as db:
            return get_incident_stats(db)


# Global instance
incident_manager = IncidentManager()