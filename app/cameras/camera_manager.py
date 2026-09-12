# PyroGuard Cameras Module
# Camera management and video capture

import cv2
from pathlib import Path
import time

class CameraManager:
    """Manage multiple camera sources."""
    
    def __init__(self, cameras_config=None):
        """
        Initialize camera manager.
        
        cameras_config: list of dicts with id, name, source, enabled
        """
        self.cameras = cameras_config or self._default_cameras()
        self.capitals = {}
        self._initialize_cameras()
    
    def _default_cameras(self):
        """Default camera configuration."""
        return [
            {
                "id": "camera_01",
                "name": "Main Entrance",
                "source": 0,
                "enabled": True
            },
            {
                "id": "camera_02",
                "name": "Warehouse",
                "source": "rtsp://camera-stream",
                "enabled": False
            }
        ]
    
    def _initialize_cameras(self):
        """Initialize video capture for each camera."""
        for cam in self.cameras:
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
                        print(f"Warning: Could not open camera {cam['id']}")
                except Exception as e:
                    print(f"Error initializing camera {cam['id']}: {e}")
    
    def get_frame(self, camera_id: str):
        """Get frame from a specific camera."""
        if camera_id not in self.capitals:
            return None, None
        
        cap = self.capitals[camera_id]
        ret, frame = cap.read()
        
        if ret:
            return frame, camera_id
        return None, camera_id
    
    def release_all(self):
        """Release all camera captures."""
        for cap in self.capitals.values():
            if cap.isOpened():
                cap.release()
        self.capitals.clear()