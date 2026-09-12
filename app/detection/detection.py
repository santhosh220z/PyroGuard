# PyroGuard Detection Module
# Fire and smoke detection using YOLOv8

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import time

class DetectionModel:
    """YOLO-based fire and smoke detection model."""
    
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.25, iou_threshold: float = 0.45):
        self.model_path = model_path or "models/fire_smoke_yolo.pt"
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.model = None
        self.class_names = ["fire", "smoke"]
        self.initialized = False
    
    def initialize(self):
        """Load the YOLO model."""
        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        self.model = YOLO(str(model_path))
        self.class_names = self.model.names
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
        
        start_time = time.time()
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

# Global model instance
detection_model = DetectionModel()

def detect_fire_smoke(frame):
    """Detect fire and smoke in a frame."""
    return detection_model.detect(frame)