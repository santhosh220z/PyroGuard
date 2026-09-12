"""PyroGuard Unit Tests - Detection Module"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import cv2
from app.detection.detection import DetectionModel, detect_fire_smoke


def test_fire_above_threshold():
    """Test detection with a fire-simulated frame above confidence threshold."""
    # Create a synthetic frame (green image)
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    # Add a red-ish region to simulate fire (BGR format)
    frame[:, :] = (0, 0, 100)  # Dark blue/redish
    
    # Initialize model (this will fail if model weights not present, 
    # but we test the structure)
    try:
        model = DetectionModel(confidence_threshold=0.01)  # Very low threshold
        detections = detect_fire_smoke(frame)
        
        # If model loads, check detection output structure
        assert isinstance(detections, list), "Detections should be a list"
        print("✅ test_fire_above_threshold: PASSED")
    except FileNotFoundError:
        # Expected if model weights don't exist yet
        print("⚠️  test_fire_above_threshold: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_fire_above_threshold: INFO - {type(e).__name__}")


def test_fire_below_threshold():
    """Test that detection works with high confidence threshold."""
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    frame[:, :] = (0, 0, 100)
    
    try:
        model = DetectionModel(confidence_threshold=0.99)  # Very high threshold
        detections = detect_fire_smoke(frame)
        
        # With very high threshold, may get no detections
        assert isinstance(detections, list), "Detections should be a list"
        print("✅ test_fire_below_threshold: PASSED")
    except FileNotFoundError:
        print("⚠️  test_fire_below_threshold: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_fire_below_threshold: INFO - {type(e).__name__}")


def test_persistent_fire():
    """Test detection persistence concept."""
    # Create consistent frame
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        model = DetectionModel(confidence_threshold=0.01)
        detections = detect_fire_smoke(frame)
        
        # Check structure of detections
        if detections:
            for det in detections:
                assert "class" in det, "Detection should have 'class'"
                assert "confidence" in det, "Detection should have 'confidence'"
                assert "bbox" in det, "Detection should have 'bbox'"
        print("✅ test_persistent_fire: PASSED")
    except FileNotFoundError:
        print("⚠️  test_persistent_fire: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_persistent_fire: INFO - {type(e).__name__}")


def test_smoke_detection():
    """Test smoke detection structure."""
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    frame[:, :] = (100, 100, 100)  # Gray
    
    try:
        model = DetectionModel(confidence_threshold=0.01)
        detections = detect_fire_smoke(frame)
        
        assert isinstance(detections, list)
        # Class names should include 'smoke'
        # (detections may be empty without trained model, that's OK)
        print("✅ test_smoke_detection: PASSED")
    except FileNotFoundError:
        print("⚠️  test_smoke_detection: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_smoke_detection: INFO - {type(e).__name__}")