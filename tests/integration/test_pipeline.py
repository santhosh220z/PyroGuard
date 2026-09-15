# PyroGuard Integration Test
# End-to-end flow: detection -> temporal verification -> confirmed state

import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DRY_RUN"] = "true"

import numpy as np

from app.detection.pipeline import DetectionPipeline, STATE_NORMAL, STATE_WARNING
from app.detection.detection import DetectionModel


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
            "timestamp": time.time(),
        }]

    def verify_temporal(self, detections):
        return self._temporal.verify_temporal(detections)


def test_pipeline_end_to_end():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    model = FakeModel(fire=True)

    pipeline = DetectionPipeline(
        camera_config={"id": "camera_01", "name": "Test", "source": 0, "enabled": True},
        model=model, display=False,
    )

    # Frame 1: candidate, not confirmed
    pipeline.process_frame(frame)
    assert pipeline.state == STATE_WARNING, f"Expected WARNING, got {pipeline.state}"

    # Frames 2-3: reach confirmation threshold (default 3)
    pipeline.process_frame(frame)
    pipeline.process_frame(frame)
    assert pipeline.state == "FIRE_DETECTED", f"Expected FIRE_DETECTED, got {pipeline.state}"

    # Bounding-box overlays draw without error
    annotated = pipeline.draw_overlays(frame.copy())
    assert annotated is not None

    print("? test_pipeline_end_to_end: PASSED")


def test_pipeline_no_fire():
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    model = FakeModel(fire=False)

    pipeline = DetectionPipeline(
        camera_config={"id": "camera_01", "name": "Test", "source": 0, "enabled": True},
        model=model, display=False,
    )

    for _ in range(10):
        pipeline.process_frame(frame)
        assert pipeline.state == STATE_NORMAL, f"Expected NORMAL, got {pipeline.state}"

    print("? test_pipeline_no_fire: PASSED")


if __name__ == "__main__":
    test_pipeline_end_to_end()
    test_pipeline_no_fire()
    print("All integration tests passed")
