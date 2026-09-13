# PyroGuard Evidence Capture Module
# Captures evidence on confirmed fire events

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


class EvidenceCapture:
    """Captures snapshots, metadata, and event logs for confirmed incidents."""

    def __init__(self, base_dir: str = "data/incidents"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_dirname(self, camera_id: str) -> str:
        """Sanitize camera id for filesystem use (blocks traversal like '..')."""
        return re.sub(r"[^A-Za-z0-9_-]", "_", str(camera_id))

    def capture(self, frame: np.ndarray, camera_id: str, detected_class: str,
                confidence: float, bounding_box: list) -> dict:
        """
        Capture evidence for a confirmed fire event.

        Creates data/incidents/{timestamp}_{camera_id}/ containing:
        - snapshot.jpg
        - metadata.json
        - event.log

        Returns dict with incident_id and file paths.
        """
        timestamp = datetime.now()
        incident_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{self._safe_dirname(camera_id)}_{uuid.uuid4().hex[:8]}"

        incident_dir = self.base_dir / incident_id
        incident_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = incident_dir / "snapshot.jpg"
        metadata_path = incident_dir / "metadata.json"
        event_log_path = incident_dir / "event.log"

        # Save snapshot
        saved_snapshot = False
        if frame is not None:
            try:
                cv2.imwrite(str(snapshot_path), frame)
                saved_snapshot = True
            except Exception as e:
                self._append_log(event_log_path, f"snapshot_failed: {e}")

        # Save metadata
        metadata = {
            "incident_id": incident_id,
            "timestamp": timestamp.isoformat(),
            "camera_id": camera_id,
            "detected_class": detected_class,
            "confidence": float(confidence),
            "bounding_box": [float(v) for v in bounding_box] if bounding_box else None,
            "snapshot": snapshot_path.name if saved_snapshot else None,
        }
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self._append_log(event_log_path, f"metadata_failed: {e}")

        # Initialize event log
        self._append_log(event_log_path, f"incident_created class={detected_class} confidence={confidence:.3f}")

        return {
            "incident_id": incident_id,
            "incident_dir": str(incident_dir),
            "snapshot_path": str(snapshot_path) if saved_snapshot else None,
            "metadata_path": str(metadata_path),
            "event_log_path": str(event_log_path),
        }

    @staticmethod
    def _append_log(path: Path, message: str):
        """Append a line to the incident event log."""
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {message}\n")
        except Exception:
            pass  # Logging must never crash the detection system