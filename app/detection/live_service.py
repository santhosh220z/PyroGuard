# PyroGuard Live Detection Service
# Single background thread that owns the camera capture (so the camera is read
# by exactly one reader, avoiding VideoCapture conflicts), runs the YOLO model
# + temporal verification continuously, and publishes a thread-safe snapshot
# that the API/UI can poll for real-time predictions.

import threading
import time
from datetime import datetime

from app.detection.detection import DetectionModel
from app.detection.pipeline import STATE_NORMAL, STATE_WARNING, STATE_FIRE_DETECTED


class LiveDetectionService:
    """Continuously detect fire/smoke on the primary camera."""

    PROCESS_INTERVAL = 0.15  # seconds between processed frames

    def __init__(self, cameras_config, model_path, confidence_threshold=0.25,
                 iou_threshold=0.45, confirmation_frames=3, confirmation_window=5.0):
        from app.cameras.camera_manager import CameraManager
        self._manager = CameraManager(cameras_config=cameras_config)
        self._model = DetectionModel(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            confirmation_frames=confirmation_frames,
            confirmation_window=confirmation_window,
        )
        self._lock = threading.Lock()
        self._latest_frames = {}  # cam_id -> numpy frame
        self._latest_detections = {}  # cam_id -> list of detections
        self._states = {}  # cam_id -> pipeline state string
        self._fps = {}  # cam_id -> measured fps (frames in last 1s window)
        self._frame_counts = {}  # cam_id -> frames in current window
        self._window_start = time.time()
        self._model_loaded = False
        self._model_error = None
        self._start_time = time.time()
        self._stop = threading.Event()
        self._thread = None

    @property
    def manager(self):
        return self._manager

    @property
    def model_loaded(self):
        return self._model_loaded

    @property
    def model_error(self):
        return self._model_error

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pyroguard-live-detection", daemon=True)
        self._thread.start()

    def stop(self, timeout=3):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._manager.release_all()

    def _run(self):
        try:
            self._model.initialize()
            self._model_loaded = True
            print("Live detection model loaded")
        except Exception as e:
            self._model_error = str(e)
            print(f"Live detection model failed to load: {e}")

        enabled = [c for c in self._manager.cameras if c.get("enabled")]
        primary = self._primary_camera_id()
        last_process = 0.0

        while not self._stop.is_set():
            now = time.time()
            for cam in enabled:
                cam_id = cam["id"]
                frame, _ = self._manager.get_frame(cam_id)
                if frame is None:
                    continue
                with self._lock:
                    self._latest_frames[cam_id] = frame
                    self._frame_counts[cam_id] = self._frame_counts.get(cam_id, 0) + 1
                if now >= last_process + self.PROCESS_INTERVAL:
                    self._process_primary(primary)
                    last_process = now

            # fps: frames read within a rolling 1s window
            if now - self._window_start >= 1.0:
                elapsed = now - self._window_start
                with self._lock:
                    self._fps = {
                        cam_id: round(count / elapsed, 2)
                        for cam_id, count in self._frame_counts.items()
                    }
                    self._frame_counts = {}
                self._window_start = now

            time.sleep(0.02)

    def _primary_camera_id(self):
        for c in self._manager.cameras:
            if c.get("enabled"):
                return c["id"]
        return None

    def _process_primary(self, cam_id):
        if cam_id is None or not self._model_loaded:
            return

        with self._lock:
            frame = self._latest_frames.get(cam_id)
        if frame is None:
            return

        try:
            detections = self._model.detect(frame)
            verification = self._model.verify_temporal(detections)
        except Exception:
            return

        if verification["fire_confirmed"]:
            state = STATE_FIRE_DETECTED
        elif verification["confirmation_counter"] > 0:
            state = STATE_WARNING
        else:
            state = STATE_NORMAL

        with self._lock:
            self._latest_detections[cam_id] = detections
            self._states[cam_id] = state

    def get_frame(self, cam_id):
        """Latest frame for cam_id (or None if camera hasn't produced one yet)."""
        with self._lock:
            return self._latest_frames.get(cam_id)

    def get_live_status(self):
        """Thread-safe snapshot of live detection state for all cameras."""
        now = time.time()
        result = {
            "model_loaded": self._model_loaded,
            "model_error": self._model_error,
            "capture_started": bool(self._latest_frames),
            "uptime": round(now - self._start_time, 1),
            "cameras": {},
        }
        with self._lock:
            for cam in self._manager.cameras:
                cam_id = cam["id"]
                detections = self._latest_detections.get(cam_id, [])
                best = max(detections, key=lambda d: d["confidence"]) if detections else None

                status = self._manager.get_camera_status(cam_id)
                state = self._states.get(cam_id, STATE_NORMAL)

                # detection persistence time = age of the best detection
                persisted = None
                if best and best.get("timestamp"):
                    persisted = round(now - best["timestamp"], 1)

                result["cameras"][cam_id] = {
                    "name": cam["name"],
                    "state": state,
                    "status": status.get("status"),
                    "fps": self._fps.get(cam_id, 0.0),
                    "last_frame_timestamp": status.get("last_frame_timestamp"),
                    "detection_count": len(detections),
                    "best_detection": best,
                    "persisted_seconds": max(persisted, 0) if persisted is not None else None,
                    "fire_confirmed": self._model.fire_confirmed,
                    "confirmation_counter": self._model.confirmation_counter,
                    "confirmation_frames": self._model.confirmation_frames,
                }
        return result


# Shared singleton used by the API routes.
_service = None
_service_lock = threading.Lock()


def get_live_service(cameras_config=None, model_path=None,
                     confidence_threshold=None, iou_threshold=None,
                     confirmation_frames=None, confirmation_window=None):
    """Get the shared LiveDetectionService instance (created once)."""
    global _service
    with _service_lock:
        if _service is None:
            from app.config.config import settings
            _service = LiveDetectionService(
                cameras_config=cameras_config if cameras_config is not None else settings.CAMERAS,
                model_path=model_path if model_path else settings.MODEL_PATH,
                confidence_threshold=confidence_threshold if confidence_threshold is not None else settings.CONFIDENCE_THRESHOLD,
                iou_threshold=iou_threshold if iou_threshold is not None else settings.IOU_THRESHOLD,
                confirmation_frames=confirmation_frames if confirmation_frames is not None else settings.CONFIRMATION_FRAMES,
                confirmation_window=confirmation_window if confirmation_window is not None else settings.CONFIRMATION_WINDOW,
            )
    return _service