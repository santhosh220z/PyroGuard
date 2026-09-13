# PyroGuard Integration Test
# End-to-end flow: detection -> temporal verify -> evidence -> DB -> alerts (dry-run)

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os

os.environ["DRY_RUN"] = "true"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["WEBHOOK_URL"] = ""

import tempfile

import numpy as np

from app.detection.pipeline import DetectionPipeline, STATE_NORMAL, STATE_WARNING
from app.detection.detection import DetectionModel
from app.alerts.alert_service import AlertService
from app.incidents.incident_db import IncidentDatabase
from app.incidents.evidence_capture import EvidenceCapture


class FakeModel:
    """Deterministic stand-in for YOLO inference (no weights required).
    Temporal verification is delegated to the real DetectionModel logic,
    which is pure state management and needs no trained weights."""

    def __init__(self, fire=True):
        self.fire = fire
        self.call_count = 0
        self._temporal = DetectionModel(confirmation_frames=3)

    def detect(self, frame):
        self.call_count += 1
        if not self.fire:
            return []
        return [{
            "class": "fire",
            "confidence": 0.9,
            "bbox": [100.0, 100.0, 200.0, 200.0],
            "timestamp": __import__("time").time(),
        }]

    def verify_temporal(self, detections):
        return self._temporal.verify_temporal(detections)


def test_pipeline_end_to_end():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    with tempfile.TemporaryDirectory() as tmp:
        db = IncidentDatabase(db_path=str(Path(tmp) / "incidents.db"))
        evidence = EvidenceCapture(base_dir=str(Path(tmp) / "incidents"))
        alerts = AlertService()
        model = FakeModel(fire=True)

        pipeline = DetectionPipeline(
            camera_config={"id": "camera_01", "name": "Test", "source": 0, "enabled": True},
            model=model, db=db, evidence=evidence, alerts=alerts, display=False,
        )

        # Frame 1: candidate, not confirmed
        pipeline.process_frame(frame)
        assert pipeline.state == STATE_WARNING, f"Expected WARNING, got {pipeline.state}"
        assert len(db.list_incidents()) == 0, "No incident before confirmation"

        # Frames 2-3: reach confirmation threshold (default 3)
        pipeline.process_frame(frame)
        pipeline.process_frame(frame)
        assert pipeline.state == "FIRE_DETECTED", f"Expected FIRE_DETECTED, got {pipeline.state}"

        # Evidence captured
        incident_id = pipeline.evidence.last_incident_id if hasattr(pipeline.evidence, "last_incident_id") else None

        # Incident recorded in DB
        incidents = db.list_incidents()
        assert len(incidents) >= 1, "Incident should be recorded after confirmation"

        # Alert workflow ran in dry-run without crashing
        print("✅ test_pipeline_end_to_end: PASSED")


def test_pipeline_no_fire():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    with tempfile.TemporaryDirectory() as tmp:
        db = IncidentDatabase(db_path=str(Path(tmp) / "incidents.db"))
        evidence = EvidenceCapture(base_dir=str(Path(tmp) / "incidents"))
        alerts = AlertService()
        model = FakeModel(fire=False)

        pipeline = DetectionPipeline(
            camera_config={"id": "camera_01", "name": "Test", "source": 0, "enabled": True},
            model=model, db=db, evidence=evidence, alerts=alerts, display=False,
        )

        for _ in range(10):
            pipeline.process_frame(frame)
            assert pipeline.state == STATE_NORMAL, f"Expected NORMAL, got {pipeline.state}"

        assert len(db.list_incidents()) == 0, "No incidents without fire"
        print("✅ test_pipeline_no_fire: PASSED")


def test_evidence_capture_files():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    with tempfile.TemporaryDirectory() as tmp:
        evidence = EvidenceCapture(base_dir=str(Path(tmp) / "incidents"))
        result = evidence.capture(
            frame=frame, camera_id="camera_01", detected_class="fire",
            confidence=0.9, bounding_box=[10, 10, 50, 50],
        )

        incident_dir = Path(result["incident_dir"])
        assert incident_dir.exists(), "Incident directory should exist"
        assert (incident_dir / "metadata.json").exists(), "metadata.json should exist"
        assert (incident_dir / "event.log").exists(), "event.log should exist"
        assert (incident_dir / "snapshot.jpg").exists(), "snapshot.jpg should exist"

        # Filename sanitization: camera id with unsafe chars
        result2 = evidence.capture(
            frame=frame, camera_id="../../evil", detected_class="fire",
            confidence=0.9, bounding_box=None,
        )
        assert ".." not in result2["incident_id"], "Unsafe chars must be sanitized"

        print("✅ test_evidence_capture_files: PASSED")


if __name__ == "__main__":
    test_pipeline_end_to_end()
    test_pipeline_no_fire()
    test_evidence_capture_files()
    print("All integration tests passed")