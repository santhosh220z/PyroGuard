#!/usr/bin/env python3
"""
PyroGuard YOLOv11s Training Script
Trains a YOLOv11s (small) model for fire and smoke detection.
Saves as models/fire_smoke_yolo11s.pt - keeps the existing yolov11n model intact.
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_dataset import main as prepare_dataset_main

# Training configuration for YOLOv11s
TRAINING_CONFIG = {
    "image_size": 640,
    "batch_size": 16,
    "epochs": 50,
    "learning_rate": 0.01,
    "optimizer": "SGD",
    "augmentation": True,
    "device": "cuda",
    "workers": 4,
    "pretrained_weights": "yolo11s.pt",  # YOLOv11s pretrained weights
}

def run_yolo11s_training():
    """Execute the YOLOv11s training pipeline."""
    print("=" * 60)
    print("PYROGUARD YOLOv11s MODEL TRAINING")
    print("=" * 60)
    print()
    
    # Ensure dataset is prepared
    print("STAGE 1: Preparing dataset...")
    if not prepare_dataset_main():
        print("❌ Dataset preparation failed. Aborting.")
        return False
    print("✅ Dataset preparation complete")
    print()
    
    # Train model
    print("STAGE 2: Training YOLOv11s model...")
    try:
        from ultralytics import YOLO
        import torch
        
        config = TRAINING_CONFIG
        final_model_path = PROJECT_ROOT / "models" / "fire_smoke_yolo11s.pt"
        
        # Load pretrained YOLOv11s model
        print(f"Loading pretrained weights: {config['pretrained_weights']}")
        model = YOLO(config["pretrained_weights"])
        
        # Determine device
        device = config["device"]
        if not torch.cuda.is_available() and device == "cuda":
            device = "cpu"
            print("⚠️  CUDA not available, falling back to CPU")
        else:
            print(f"Using device: {device}")
        
        # Train the model
        print("Starting training...")
        results = model.train(
            data=str(PROJECT_ROOT / "datasets/processed/data.yaml"),
            epochs=config["epochs"],
            imgsz=config["image_size"],
            batch=config["batch_size"],
            lr0=config["learning_rate"],
            optimizer=config["optimizer"],
            device=device,
            workers=config["workers"],
            augment=config["augmentation"],
            verbose=True,
            name="yolo11s_fire_smoke",
        )
        
        print(f"✅ Training complete. Best model saved to {results.save_dir}")
        print()
        
        # Copy best model to project models directory
        best_model_path = Path(results.save_dir) / "weights" / "best.pt"
        
        if best_model_path.exists():
            shutil.copy2(str(best_model_path), str(final_model_path))
            print(f"✅ YOLOv11s model saved to {final_model_path}")
        else:
            print(f"⚠️  Best model not found at expected path: {best_model_path}")
            return False
        
        print()
        print("=" * 60)
        print("YOLOv11s TRAINING COMPLETE")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"❌ Required library not available: {e}")
        print("Install with: pip install ultralytics torch")
        return False
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_yolo11s_training()
    exit(0 if success else 1)