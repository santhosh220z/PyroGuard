# PyroGuard Cameras Module
# Camera management and video capture with health monitoring

import cv2
from pathlib import Path
import time
from collections import deque


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
        """
        self.cameras = cameras_config or self._default_cameras()
        self.capitals = {}
        self.health_status = {}  # Per-camera health status
        self.frame_timestamps = {}  # Per-camera last frame timestamps
        self.failed_frames = {}  # Per-camera failed frame count
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
    
    def _initialize_cameras(self):
        """Initialize video capture for each camera."""
        for cam in self.cameras:
            self.health_status[cam["id"]] = self.HEALTHY
            self.frame_timestamps[cam["id"]] = time.time()
            self.failed_frames[cam["id"]] = 0
            
            if cam["enabled"]:
                try:
                    source = cam["source"]
                    if isinstance(source, str) and source.startswith("rtsp"):
                        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                    else:
                        cap = cv2.VideoCapture(int(source))
                    
                    if cap.isOpened():
                        self.capitals[cam["id"]] = cap
                        print(f"Camera {cam['id']} ({cam['name']}) initialized")
                    else:
                        self._set_camera_status(cam["id"], self.ERROR)
                        print(f"Warning: Could not open camera {cam['id']}")
                except Exception as e:
                    self._set_camera_status(cam["id"], self.ERROR)
                    print(f"Error initializing camera {cam['id']}: {e}")
    
    def _set_camera_status(self, camera_id: str, status: str):
        """Set camera health status."""
        self.health_status[camera_id] = status
    
    def get_frame(self, camera_id: str):
        """Get frame from a specific camera with health tracking."""
        if camera_id not in self.capitals:
            self._set_camera_status(camera_id, self.ERROR)
            return None, camera_id
        
        cap = self.capitals[camera_id]
        start_time = time.time()
        
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
        
        cap = self.capitals[camera_id]
        fps = 0
        if camera_id in self.frame_timestamps:
            elapsed = time.time() - self.frame_timestamps[camera_id]
            if elapsed > 0:
                fps = round(1.0 / elapsed, 2) if self.frame_timestamps[camera_id] else 0
        
        return {
            "status": self.health_status.get(camera_id, self.ERROR),
            "fps": fps,
            "failed_frames": self.failed_frames.get(camera_id, 0),
            "is_opened": cap.isOpened() if cap else False,
            "last_frame_timestamp": self.frame_timestamps.get(camera_id)
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