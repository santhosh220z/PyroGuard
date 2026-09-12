#!/usr/bin/env python3
"""
PyroGuard Camera Test Script
Tests camera connectivity and basic functionality.

Usage: python scripts/test_camera.py --source 0
or:  python scripts/test_camera.py --source rtsp://url
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.cameras.camera_manager import CameraManager


def test_camera(source=0, camera_id="test_cam"):
    """Test a camera source."""
    print(f"Testing camera {camera_id} with source: {source}")
    print()
    
    # Create camera manager with single camera config
    cameras = [
        {
            "id": camera_id,
            "name": "Test Camera",
            "source": source,
            "enabled": True
        }
    ]
    
    manager = CameraManager(cameras=cameras)
    
    # Try to get a frame
    frame, cid = manager.get_frame(camera_id)
    
    if frame is not None:
        print(f"✅ Camera {camera_id} is working")
        print(f"   Frame shape: {frame.shape}")
        return True
    else:
        print(f"❌ Camera {camera_id} failed to provide frame")
        return False


def main():
    parser = argparse.ArgumentParser(description="PyroGuard Camera Test")
    parser.add_argument("--source", type=str, default=0,
                        help="Camera source (0 for webcam, or RTSP URL)")
    parser.add_argument("--camera-id", type=str, default="test_cam",
                        help="Camera ID")
    
    args = parser.parse_args()
    
    success = test_camera(source=args.source, camera_id=args.camera_id)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()