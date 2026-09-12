#!/usr/bin/env python3
"""
PyroGuard Model Training Script
Trains a YOLOv8 model for fire and smoke detection.

Stages (from config):
1. prepare_dataset
2. validate_dataset
3. train_model
4. validate_model
5. evaluate_model
6. save_best_model

Configurable parameters:
- image_size
- batch_size
- epochs
- learning_rate
- optimizer
- augmentation
- device
- workers
- pretrained_weights
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_dataset import main as prepare_dataset_main

# Training configuration (from configs/config.yaml)
TRAINING_CONFIG = {
    "image_size": 640,
    "batch_size": 16,
    "epochs": 50,
    "learning_rate": 0.01,
    "optimizer": "SGD",
    "augmentation": True,
    "device": "cuda",  # Will fall back to cpu if unavailable
    "workers": 4,
    "pretrained_weights": "yolo11n.pt",  # Ultralytics default
}


def run_training_pipeline():
    """Execute the full training pipeline."""
    print("=" * 60)
    print("PYROGUARD MODEL TRAINING PIPELINE")
    print("=" * 60)
    print()
    
    # Stage 1: Prepare dataset
    print("STAGE 1: Preparing dataset...")
    if not prepare_dataset_main():
        print("❌ Dataset preparation failed. Aborting.")
        return False
    print("✅ Dataset preparation complete")
    print()
    
    # Stage 2: Validate dataset (already done in prepare_dataset)
    print("STAGE 2: Dataset validation - already completed during preparation")
    print()
    
    # Stage 3: Train model
    print("STAGE 3: Training model...")
    try:
        from ultralytics import YOLO
        import torch
        
        config = TRAINING_CONFIG
        model_path = "models/fire_smoke_yolo.pt"
        
        # Load pretrained model
        model = YOLO(config["pretrained_weights"])
        
        # Determine device
        device = config["device"]
        if not torch.cuda.is_available() and device == "cuda":
            device = "cpu"
            print("⚠️  CUDA not available, falling back to CPU")
        
        # Train the model
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
            verbose=True
        )
        
        print(f"✅ Training complete. Best model saved to {results.save_dir}")
        print()
        
        # Stage 4: Validate model (included in training)
        print("STAGE 4: Model validation - completed during training")
        print()
        
        # Stage 5: Evaluate model
        print("STAGE 5: Evaluating model...")
        # Validation metrics are included in training results
        print("✅ Evaluation metrics available in training results")
        print()
        
        # Stage 6: Save best model
        best_model_path = Path(results.save_dir) / "weights" / "best.pt"
        final_model_path = Path(model_path)
        
        # Copy best model to project models directory
        if best_model_path.exists():
            shutil.copy2(str(best_model_path), str(final_model_path))
            print(f"✅ Best model saved to {final_model_path}")
        else:
            print(f"⚠️  Best model not found at expected path")
        
        print()
        print("=" * 60)
        print("TRAINING PIPELINE COMPLETE")
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
    success = run_training_pipeline()
    exit(0 if success else 1)