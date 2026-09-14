# PyroGuard Real-Time Detection Pipeline
# Ties together camera capture, detection, temporal verification,
# evidence capture, incident database, and alert automation.

import time
from datetime import datetime

import cv2

from app.cameras.camera_manager import CameraManager
from app.detection.detection import DetectionModel
from app.alerts.alert_service import AlertService
from app.incidents.incident_db import IncidentDatabase
from app.incidents.evidence_capture import EvidenceCapture

# System state (per dashboard spec)
STATE_NORMAL = "NORMAL"
STATE_WARNING = "WARNING"
STATE_FIRE_DETECTED = "FIRE_DETECTED"


class DetectionPipeline:
    """Real-time fire/smoke detection pipeline for a single camera."""

    def __init__(self, camera_config: dict, model: DetectionModel,
                 db: IncidentDatabase, evidence: EvidenceCapture,
                 alerts: AlertService, display: bool = True):
        self.camera_config = camera_config
        self.camera_id = camera_config["id"]
        self.model = model
        self.db = db
        self.evidence = evidence
        self.alerts = alerts
        self.display = display

        self.state = STATE_NORMAL
        self.current_confidence = 0.0
        self.current_detections = []
        self.running = False

    def process_frame(self, frame):
        """Process a single frame and update state. Returns the annotated state."""
        detections = self.model.detect(frame)
        verification = self.model.verify_temporal(detections)

        self.current_detections = detections
        self.current_confidence = max((d["confidence"] for d in detections), default=0.0)

        if verification["fire_confirmed"]:
            # Fire just confirmed - run the alert workflow
            self._handle_fire_confirmed(frame, verification["detection_data"])
            self.state = STATE_FIRE_DETECTED
        elif verification["confirmation_counter"] > 0:
            # Candidate fire detected but not yet confirmed
            print(f"[{self.camera_id}] fire_candidate_detected "
                  f"({verification['confirmation_counter']} confirmation frames)")
            self.state = STATE_WARNING
        else:
            self.state = STATE_NORMAL

        return frame

    def _handle_fire_confirmed(self, frame, detection_data):
        """Alert workflow: capture evidence, create incident, send alert."""
        detection_data = detection_data or {
            "class": "fire", "confidence": 0.0, "bbox": None, "timestamp": time.time()
        }
        print(f"[{self.camera_id}] fire_confirmed "
              f"class={detection_data['class']} confidence={detection_data['confidence']:.3f}")

        # 1. Capture evidence (snapshot, metadata, event log)
        evidence_info = self.evidence.capture(
            frame=frame,
            camera_id=self.camera_id,
            detected_class=detection_data["class"],
            confidence=detection_data["confidence"],
            bounding_box=detection_data.get("bbox"),
        )

        # 2. Create incident in database
        try:
            self.db.create_incident(
                incident_id=evidence_info["incident_id"],
                timestamp=datetime.now().isoformat(),
                camera_id=self.camera_id,
                event_type=detection_data["class"],
                confidence=detection_data["confidence"],
                snapshot_path=evidence_info["snapshot_path"],
            )
            print(f"[{self.camera_id}] incident_created {evidence_info['incident_id']}")
        except Exception as e:
            print(f"[{self.camera_id}] database_failure: {e}")

        # 3. Send alert (async, non-blocking; failures never crash the pipeline)
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # Running in async context - schedule as task
                loop.create_task(self.alerts.send_alert(evidence_info["incident_id"], detection_data))
            except RuntimeError:
                # No running loop - safe to use asyncio.run
                asyncio.run(self.alerts.send_alert(evidence_info["incident_id"], detection_data))
        except Exception as e:
            print(f"[{self.camera_id}] alert_failed: {e}")

    def draw_overlays(self, frame):
        """Draw bounding boxes and status overlay on the frame."""
        for det in self.current_detections:
            x1, y1, x2, y2 = (int(v) for v in det["bbox"])
            color = (0, 0, 255) if det["class"] == "fire" else (0, 165, 255)
            label = f"{det['class']} {det['confidence']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        state_color = {
            STATE_NORMAL: (0, 255, 0),
            STATE_WARNING: (0, 165, 255),
            STATE_FIRE_DETECTED: (0, 0, 255),
        }[self.state]
        cv2.putText(frame, f"{self.camera_id} | {self.state} | conf={self.current_confidence:.2f}",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        return frame

    def run(self):
        """Main loop: capture frames, detect, display. Stop with 'q' or Ctrl+C."""
        manager = CameraManager([self.camera_config])
        self.running = True
        fps = 0.0
        last_time = time.time()

        try:
            while self.running:
                frame, _ = manager.get_frame(self.camera_id)
                if frame is None:
                    time.sleep(0.1)
                    continue

                self.process_frame(frame)

                now = time.time()
                if now > last_time:
                    fps = 1.0 / (now - last_time)
                last_time = now

                if self.display:
                    annotated = self.draw_overlays(frame.copy())
                    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 56),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.imshow("PyroGuard", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        self.running = False
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            manager.release_all()
            if self.display:
                cv2.destroyAllWindows()


def run_pipeline(camera_source=0, camera_id="camera_01", camera_name="Camera",
                 model_path="models/fire_smoke_yolo.pt", display=True):
    """Convenience entry point to start the full pipeline."""
    model = DetectionModel(model_path=model_path)
    model.initialize()

    db = IncidentDatabase()
    evidence = EvidenceCapture()
    alerts = AlertService()

    pipeline = DetectionPipeline(
        camera_config={"id": camera_id, "name": camera_name, "source": camera_source, "enabled": True},
        model=model, db=db, evidence=evidence, alerts=alerts, display=display,
    )
    pipeline.run()
    return pipeline