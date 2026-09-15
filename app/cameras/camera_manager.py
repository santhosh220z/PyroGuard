# PyroGuard Cameras Module
# Camera management and video capture with health monitoring

import cv2
from pathlib import Path
import time
from collections import deque

from app.config.config import PROJECT_ROOT


class CameraManager:
    """Manage multiple camera sources with health monitoring."""
    
    # Camera health status
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ERROR = "ERROR"
    
    def __init__(self, cameras_config=None):
        """
        Initialize camera manager.
        
        cameras_config: list of dicts with id, name, source, enabled
        source can be an int (webcam index), an rtsp:// URL, or a local video file path.
        """
        self.cameras = cameras_config or self._default_cameras()
        self.capitals = {}
        self.health_status = {}  # Per-camera health status
        self.frame_timestamps = {}  # Per-camera last frame timestamps
        self.failed_frames = {}  # Per-camera failed frame count
        self.file_sources = {}  # Per-camera flag: source is a video file (loop when it ends)
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
                "name": "Main Entrance",
                "source": 0,
                "enabled": True
            }
        ]

    def _resolve_source(self, source):
        """Resolve a camera source value (int index, rtsp URL, or video file path)."""
        if isinstance(source, str) and source.startswith("rtsp"):
            return source, "rtsp"
        if isinstance(source, str):
            video_path = Path(source).expanduser()
            if not video_path.is_file():
                candidate = PROJECT_ROOT / source
                if candidate.is_file():
                    video_path = candidate
            if video_path.is_file():
                return str(video_path), "file"
            return source, "unknown"
        return int(source), "device"

    def _open_capture(self, source):
        """Open a VideoCapture for the given source. Returns (cap, kind)."""
        source_resolved, kind = self._resolve_source(source)
        if kind == "rtsp":
            cap = cv2.VideoCapture(source_resolved, cv2.CAP_FFMPEG)
        elif kind == "file":
            cap = cv2.VideoCapture(source_resolved)
            if not cap.isOpened():
                cap = cv2.VideoCapture(source_resolved, cv2.CAP_FFMPEG)
        elif kind == "unknown":
            cap = cv2.VideoCapture(source_resolved, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(source_resolved)
        return cap, kind

    def set_source(self, camera_id: str, source):
        """Replace a camera's capture source at runtime (e.g., a demo video upload)."""
        cam = next((c for c in self.cameras if c["id"] == camera_id), None)
        if cam is None:
            return {"error": f"Camera {camera_id} not found"}

        try:
            cap, kind = self._open_capture(source)
        except Exception as e:
            return {"error": f"Could not open source: {e}"}

        if not cap.isOpened():
            return {"error": f"Source did not open: {source}"}

        old_cap = self.capitals.get(camera_id)
        if old_cap:
            old_cap.release()

        cam["source"] = source
        self.capitals[camera_id] = cap
        self.file_sources[camera_id] = kind == "file"
        self.failed_frames[camera_id] = 0
        self.frame_timestamps[camera_id] = time.time()
        self._set_camera_status(camera_id, self.HEALTHY)
        print(f"Camera {camera_id} source updated to {source} - status: HEALTHY")
        return {"ok": True, "status": self.HEALTHY, "source": source}

    def _initialize_cameras(self):
        """Initialize video capture for each camera."""
        for cam in self.cameras:
            self.health_status[cam["id"]] = self.HEALTHY
            self.frame_timestamps[cam["id"]] = time.time()
            self.failed_frames[cam["id"]] = 0
            self.file_sources[cam["id"]] = False
            
            if cam["enabled"]:
                try:
                    cap, kind = self._open_capture(cam["source"])
                    self.file_sources[cam["id"]] = kind == "file"
                    
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
            cap, kind = self._open_capture(cam["source"])
        except Exception:
            return None, camera_id

        if not cap.isOpened():
            return None, camera_id

        self.capitals[camera_id] = cap
        self.file_sources[camera_id] = kind == "file"
        self.failed_frames[camera_id] = 0
        self.frame_timestamps[camera_id] = time.time()
        self._set_camera_status(camera_id, self.HEALTHY)
        print(f"Camera {camera_id} reconnected - status: HEALTHY")
        return self.get_frame(camera_id)
    
    def _set_camera_status(self, camera_id: str, status: str):
        """Set camera health status."""
        self.health_status[camera_id] = status
    
    def get_frame(self, camera_id: str):
        """Get frame from a specific camera with health tracking."""
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
            # File sources: when a recording reaches its end, loop back to frame 0
            # so a demo video plays endlessly like a live feed.
            if self.file_sources.get(camera_id):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if ret:
                    self.frame_timestamps[camera_id] = time.time()
                    self.failed_frames[camera_id] = 0
                    if self.health_status.get(camera_id) != self.HEALTHY:
                        self._set_camera_status(camera_id, self.HEALTHY)
                        print(f"Camera {camera_id} recovering - status: HEALTHY")
                    return frame, camera_id

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
            "is_file_source": bool(self.file_sources.get(camera_id, False)),
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
        self.file_sources.clear()
        self._last_reconnect.clear()