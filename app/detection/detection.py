# PyroGuard Detection Module
# Fire and smoke detection using YOLOv8 with temporal verification

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import time
from collections import deque


class DetectionModel:
    """YOLO-based fire and smoke detection model with temporal verification."""
    
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.25, 
                 iou_threshold: float = 0.45, confirmation_frames: int = 3, 
                 confirmation_window: float = 5.0):
        self.model_path = model_path or "models/fire_smoke_yolo.pt"
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.confirmation_frames = confirmation_frames
        self.confirmation_window = confirmation_window  # seconds
        self.model = None
        # D-Fire class id mapping: 0 = smoke, 1 = fire (verified visually
        # against annotated samples and the dataset's own data.yaml)
        self.class_names = ["smoke", "fire"]
        self.initialized = False
        
        # Temporal verification state
        self.fire_detection_history = deque(maxlen=confirmation_frames)
        self.last_confirmation_time = 0
        self.fire_confirmed = False
        self.confirmation_counter = 0
    
    def initialize(self):
        """Load the YOLO model."""
        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        self.model = YOLO(str(model_path))
        # The checkpoint was trained against a data.yaml with swapped names
        # (0='fire', 1='smoke'); override with the verified D-Fire mapping so
        # runtime labels match reality. Training used indices only, so the
        # learned weights are unaffected.
        # Note: ultralytics >=8.2 exposes `names` as a read-only property on
        # YOLO; the underlying task model's attribute is the mutable one.
        self.model.model.names = {i: name for i, name in enumerate(self.class_names)}
        self.class_names = self.model.model.names
        self.initialized = True
        return True
    
    def detect(self, frame: np.ndarray):
        """
        Detect fire and smoke in a frame.
        
        Returns list of detections:
        [
            {
                "class": str,
                "confidence": float,
                "bbox": [x1, y1, x2, y2],
                "timestamp": float
            }
        ]
        """
        if not self.initialized:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        results = self.model.predict(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False
        )
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": bbox,
                        "timestamp": time.time()
                    })
        
        return detections
    
    def verify_temporal(self, new_detections: list) -> dict:
        """
        Verify fire detection using temporal consistency.
        
        Updates internal state and returns verification result:
        {
            "verified": bool,  # True if fire confirmed
            "confirmation_counter": int,  # Current consecutive frame count
            "fire_confirmed": bool,  # Whether fire was just confirmed
            "detection_data": dict  # Latest detection data if verified
        }
        """
        if not new_detections:
            # No detection this frame - reset history if we had fire
            if self.fire_detection_history and self.fire_detection_history[-1]["class"] == "fire":
                # Fire disappeared - reset
                self.fire_detection_history.clear()
                self.confirmation_counter = 0
                self.fire_confirmed = False
            
            return {
                "verified": False,
                "confirmation_counter": self.confirmation_counter,
                "fire_confirmed": self.fire_confirmed,
                "detection_data": None
            }
        
        # Get the best detection from this frame
        best_detection = max(new_detections, key=lambda d: d["confidence"])
        
        if best_detection["class"] == "fire":
            # Add to detection history
            self.fire_detection_history.append(best_detection)
            
            # Check if we have enough confirmations
            current_time = time.time()
            
            # Remove old detections outside the window
            while self.fire_detection_history and \
                  (current_time - self.fire_detection_history[0]["timestamp"]) > self.confirmation_window:
                self.fire_detection_history.popleft()
            
            # Update confirmation counter (based on recent detections within window)
            self.confirmation_counter = len(self.fire_detection_history)
            
            # Check if confirmed
            just_confirmed = False
            if self.confirmation_counter >= self.confirmation_frames and not self.fire_confirmed:
                self.fire_confirmed = True
                self.last_confirmation_time = current_time
                just_confirmed = True
            
            return {
                "verified": self.fire_confirmed,
                "confirmation_counter": self.confirmation_counter,
                "fire_confirmed": just_confirmed,
                "detection_data": {
                    "class": best_detection["class"],
                    "confidence": best_detection["confidence"],
                    "bbox": best_detection["bbox"],
                    "timestamp": best_detection["timestamp"]
                } if self.fire_confirmed else None
            }
        else:
            # Non-fire detection (smoke or other) - reset fire history
            if self.fire_detection_history and self.fire_detection_history[-1]["class"] == "fire":
                self.fire_detection_history.clear()
                self.confirmation_counter = 0
                self.fire_confirmed = False
            
            return {
                "verified": False,
                "confirmation_counter": self.confirmation_counter,
                "fire_confirmed": False,
                "detection_data": None
            }
    
    def reset(self):
        """Reset the temporal verification state."""
        self.fire_detection_history.clear()
        self.last_confirmation_time = 0
        self.fire_confirmed = False
        self.confirmation_counter = 0


# Global model instance
detection_model = DetectionModel()

def detect_fire_smoke(frame):
    """Detect fire and smoke in a frame."""
    detections = detection_model.detect(frame)
    return detection_model.verify_temporal(detections)


def is_fire_confirmed():
    """Check if fire has been temporally confirmed."""
    return detection_model.fire_confirmed

def get_confirmation_info():
    """Get current confirmation status information."""
    return {
        "fire_confirmed": detection_model.fire_confirmed,
        "confirmation_counter": detection_model.confirmation_counter,
        "confirmation_frames": detection_model.confirmation_frames,
        "confirmation_window": detection_model.confirmation_window,
        "history_length": len(detection_model.fire_detection_history)
    }