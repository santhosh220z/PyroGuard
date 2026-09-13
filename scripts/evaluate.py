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
    
    # Print metrics (ultralytics DetMetrics API)
    box = results.box
    precision, recall, map50, map50_95 = box.mean_results()

    print("=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)
    print(f"  mAP50: {map50:.3f}")
    print(f"  mAP50-95: {map50_95:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall: {recall:.3f}")
    print()
    print("  Per-class performance:")
    for i in box.ap_class_index:
        p, r, c_map50, c_map = box.class_result(i)
        name = results.names[i]
        print(f"    {name}: map50={c_map50:.3f}, precision={p:.3f}, recall={r:.3f}")
    
    print("=" * 60)
    return results


if __name__ == "__main__":
    evaluate_model()