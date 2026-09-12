#!/usr/bin/env python3
"""
PyroGuard Model Evaluation Script
Evaluates the trained YOLO model and generates metrics.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO


def evaluate_model(model_path: str = None):
    """Evaluate a trained YOLO model."""
    model_path = model_path or "models/fire_smoke_yolo.pt"
    model = YOLO(model_path)
    
    print("Evaluating model...")
    print(f"Model: {model_path}")
    print()
    
    # Run validation on the processed dataset
    results = model.val(data="datasets/processed/data.yaml", split="test")
    
    # Print metrics
    metrics = results.metrics
    
    print("=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)
    print(f"  mAP50: {metrics.box.map50:.3f}")
    print(f"  mAP50-95: {metrics.box.map:.3f}")
    print(f"  Precision: {metrics.mp:.3f}")
    print(f"  Recall: {metrics.mr:.3f}")
    print()
    print("  Per-class performance:")
    for i, name in enumerate(results.names.values()):
        print(f"    {name}: map50={metrics.ap[i]:.3f}, precision={metrics.p[i]:.3f}, recall={metrics.r[i]:.3f}")
    
    print("=" * 60)
    return results


if __name__ == "__main__":
    evaluate_model()