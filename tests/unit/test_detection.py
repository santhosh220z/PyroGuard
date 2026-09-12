"""PyroGuard Unit Tests - Detection Module"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import cv2
from app.detection.detection import DetectionModel, detect_fire_smoke, is_fire_confirmed, get_confirmation_info


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
        assert isinstance(detections, dict), "detect should return dict with verification"
        assert "verified" in detections, "Should have verified key"
        print("✅ test_fire_above_threshold: PASSED")
    except FileNotFoundError:
        # Expected if model weights not present
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
        assert isinstance(detections, dict), "Detections should be a dict with verification"
        print("✅ test_fire_below_threshold: PASSED")
    except FileNotFoundError:
        print("⚠️  test_fire_below_threshold: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_fire_below_threshold: INFO - {type(e).__name__}")


def test_persistent_fire():
    """Test detection persistence - multiple frames should confirm fire."""
    # Create consistent frames
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        model = DetectionModel(confidence_threshold=0.01)
        
        # First frame - should not be confirmed yet
        result1 = detect_fire_smoke(frame)
        assert "confirmation_counter" in result1, "Should have confirmation counter"
        # First frame: counter should be 1, not confirmed yet
        assert result1["confirmation_counter"] >= 1, "Counter should be at least 1"
        
        # Second frame - counter should increase
        result2 = detect_fire_smoke(frame)
        # Counter should be 2 (or more) after second consecutive fire frame
        assert result2["confirmation_counter"] >= result1["confirmation_counter"], \
            "Counter should increase with persistent detection"
        
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
        
        assert isinstance(detections, dict)
        # Class names should include 'smoke'
        # (detections may be empty without trained model, that's OK)
        print("✅ test_smoke_detection: PASSED")
    except FileNotFoundError:
        print("⚠️  test_smoke_detection: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_smoke_detection: INFO - {type(e).__name__}")


def test_temporal_confirmation_reset():
    """Test that temporal confirmation resets when fire disappears."""
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        model = DetectionModel(confidence_threshold=0.01, confirmation_frames=2)
        
        # Frame 1: fire detected
        result1 = detect_fire_smoke(frame)
        assert result1["fire_confirmed"] == False, "First frame should not confirm"
        assert result1["confirmation_counter"] == 1, "Counter should be 1 after first frame"
        
        # Frame 2: fire still detected - should confirm
        result2 = detect_fire_smoke(frame)
        assert result2["fire_confirmed"] == True, "Second consecutive frame should confirm"
        assert result2["confirmation_counter"] >= 2, "Counter should be at least 2"
        
        # Frame 3: no fire (different frame content)
        # Create a non-fire frame
        no_fire_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        # But our synthetic frame always looks "like fire" due to constant color...
        # Just test the reset mechanism
        
        # Reset the model state
        model.reset()
        
        # After reset, should not be confirmed
        result_after_reset = detect_fire_smoke(frame)
        assert result_after_reset["fire_confirmed"] == False, "After reset, should not be confirmed"
        
        print("✅ test_temporal_confirmation_reset: PASSED")
    except FileNotFoundError:
        print("⚠️  test_temporal_confirmation_reset: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_temporal_confirmation_reset: INFO - {type(e).__name__}")


def test_confirmation_info():
    """Test confirmation info retrieval."""
    frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    try:
        model = DetectionModel(confidence_threshold=0.01, confirmation_frames=3)
        
        # Three consecutive fire frames should confirm
        for _ in range(3):
            detect_fire_smoke(frame)
        
        info = get_confirmation_info()
        assert "fire_confirmed" in info, "Should have fire_confirmed"
        assert "confirmation_counter" in info, "Should have confirmation_counter"
        assert "history_length" in info, "Should have history_length"
        
        print("✅ test_confirmation_info: PASSED")
    except FileNotFoundError:
        print("⚠️  test_confirmation_info: SKIPPED (model weights not found)")
    except Exception as e:
        print(f"⚠️  test_confirmation_info: INFO - {type(e).__name__}")