# PyroGuard Cameras Module
# Single-camera video capture with health monitoring and reconnect

import time

import cv2


class CameraManager:
    """Manage the camera source with health monitoring."""

    # Camera health status
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def __init__(self, cameras_config=None):
        """
        Initialize camera manager.

        cameras_config: list with a single dict (id, name, source, enabled).
        source can be an int (webcam index) or an rtsp:// URL.
        """
        self.cameras = cameras_config or self._default_cameras()
        self.capitals = {}
        self.health_status = {}  # Per-camera health status
        self.frame_timestamps = {}  # Per-camera last frame timestamps
        self.failed_frames = {}  # Per-camera failed frame count
        self._last_reconnect = {}  # Per-camera reconnect throttle timestamps
        self._initialize_cameras()

    def _default_cameras(self):
        """Default camera configuration (from config.yaml CAMERAS)."""
        try:
            from app.config.config import settings
            if settings.CAMERAS:
                return settings.CAMERAS
        except ImportError:
            pass
        return [
            {
                "id": "camera_01",
                "name": "Live Camera",
                "source": 0,
                "enabled": True
            }
        ]

    def _open_capture(self, source):
        """Open a VideoCapture for the given source."""
        return cv2.VideoCapture(int(source) if not isinstance(source, str) else source)

    def _initialize_cameras(self):
        """Initialize video capture for each camera."""
        for cam in self.cameras:
            self.health_status[cam["id"]] = self.HEALTHY
            self.frame_timestamps[cam["id"]] = time.time()
            self.failed_frames[cam["id"]] = 0

            if cam["enabled"]:
                try:
                    cap = self._open_capture(cam["source"])
                    if cap.isOpened():
                        self.capitals[cam["id"]] = cap
                        print(f"Camera {cam['id']} ({cam['name']}) initialized")
                    else:
                        self._set_camera_status(cam["id"], self.ERROR)
                        print(f"Warning: Could not open camera {cam['id']}")
                except Exception as e:
                    self._set_camera_status(cam["id"], self.ERROR)
                    print(f"Error initializing camera {cam['id']}: {e}")

    def _try_reopen(self, camera_id):
        """Attempt to (re)open a camera that failed to initialize or disconnected."""
        now = time.time()
        if now - self._last_reconnect.get(camera_id, 0) < 5.0:
            return None, camera_id
        self._last_reconnect[camera_id] = now

        cam = next((c for c in self.cameras if c["id"] == camera_id), None)
        if cam is None or not cam.get("enabled"):
            return None, camera_id

        try:
            cap = self._open_capture(cam["source"])
        except Exception:
            return None, camera_id

        if not cap.isOpened():
            return None, camera_id

        self.capitals[camera_id] = cap
        self.failed_frames[camera_id] = 0
        self.frame_timestamps[camera_id] = time.time()
        self._set_camera_status(camera_id, self.HEALTHY)
        print(f"Camera {camera_id} reconnected - status: HEALTHY")
        return self.get_frame(camera_id)

    def _set_camera_status(self, camera_id: str, status: str):
        """Set camera health status."""
        self.health_status[camera_id] = status

    def get_frame(self, camera_id: str):
        """Get frame from the camera with health tracking."""
        cap = self.capitals.get(camera_id)
        if cap is None:
            self._set_camera_status(camera_id, self.ERROR)
            return None, camera_id

        if not cap.isOpened():
            return self._try_reopen(camera_id)

        ret, frame = cap.read()
        current_time = time.time()

        if ret:
            # Update health tracking
            self.frame_timestamps[camera_id] = current_time
            self.failed_frames[camera_id] = 0

            # Ensure HEALTHY status
            if self.health_status.get(camera_id) != self.HEALTHY:
                self._set_camera_status(camera_id, self.HEALTHY)
                print(f"Camera {camera_id} recovered - status: HEALTHY")

            return frame, camera_id
        else:
            # Track failed frames
            self.failed_frames[camera_id] = self.failed_frames.get(camera_id, 0) + 1

            # Check if we should mark as warning/error
            failed_count = self.failed_frames[camera_id]
            if failed_count >= 5:
                self._set_camera_status(camera_id, self.ERROR)
                print(f"Camera {camera_id} ERROR - {failed_count} consecutive failed frames")
            elif failed_count >= 2:
                self._set_camera_status(camera_id, self.WARNING)
                print(f"Camera {camera_id} WARNING - {failed_count} failed frames")

            return None, camera_id

    def get_camera_status(self, camera_id: str) -> dict:
        """Get camera health status and stats."""
        if camera_id not in self.capitals:
            return {"status": self.ERROR, "error": "Camera not initialized"}

        cap = self.capitals.get(camera_id)
        fps = 0
        if camera_id in self.frame_timestamps:
            elapsed = time.time() - self.frame_timestamps[camera_id]
            if elapsed > 0:
                fps = round(1.0 / elapsed, 2) if self.frame_timestamps[camera_id] else 0

        cam = next((c for c in self.cameras if c["id"] == camera_id), None)
        return {
            "status": self.health_status.get(camera_id, self.ERROR),
            "fps": fps,
            "failed_frames": self.failed_frames.get(camera_id, 0),
            "is_opened": cap.isOpened() if cap else False,
            "last_frame_timestamp": self.frame_timestamps.get(camera_id),
            "source": cam.get("source") if cam else None,
        }

    def release_all(self):
        """Release all camera captures."""
        for cap in self.capitals.values():
            if cap.isOpened():
                cap.release()
        self.capitals.clear()
        # Reset health tracking
        self.health_status.clear()
        self.frame_timestamps.clear()
        self.failed_frames.clear()
        self._last_reconnect.clear()
