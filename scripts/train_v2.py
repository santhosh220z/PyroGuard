#!/usr/bin/env python3
"""
PyroGuard YOLOv11s Training Script v2 (Improved Config)
Trains YOLOv11s at 960px resolution for better small-object detection.
Saves as models/fire_smoke_yolo11s_v2.pt - keeps all existing models intact.
Supports resume from checkpoint: run with --resume to continue from last checkpoint.

Config: imgsz=960, batch=8, epochs=100, patience=30, cosine LR, warmup=5
"""

import os
import sys
import shutil
import argparse
import signal
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_dataset import main as prepare_dataset_main

# Training configuration for YOLOv11s v2 (improved)
TRAINING_CONFIG = {
    "image_size": 960,
    "batch_size": 8,
    "epochs": 100,
    "learning_rate": 0.01,
    "optimizer": "SGD",
    "augmentation": True,
    "device": "cuda",
    "workers": 4,
    "pretrained_weights": "yolo11s.pt",
    # Advanced LR schedule
    "cosine_lr": True,
    "warmup_epochs": 5,
    "warmup_momentum": 0.8,
    "warmup_bias_lr": 0.1,
    # Early stopping
    "patience": 30,
    # Save checkpoints
    "save_period": 5,
    # Mixed precision for VRAM efficiency
    "amp": True,
}

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n⚠️  Interrupt received. Finishing current epoch and saving checkpoint...")
    shutdown_requested = True


def find_latest_run_dir(name_prefix: str) -> Path | None:
    """Find the latest run directory for a given experiment name."""
    runs_dir = PROJECT_ROOT / "runs" / "detect"
    if not runs_dir.exists():
        return None
    
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith(name_prefix)]
    if not run_dirs:
        return None
    
    run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return run_dirs[0]


def get_last_checkpoint(run_dir: Path) -> Path | None:
    """Get the last checkpoint file from a run directory."""
    weights_dir = run_dir / "weights"
    if not weights_dir.exists():
        return None
    
    last_ckpt = weights_dir / "last.pt"
    if last_ckpt.exists():
        return last_ckpt
    
    best_ckpt = weights_dir / "best.pt"
    if best_ckpt.exists():
        return best_ckpt
    
    epoch_ckpts = list(weights_dir.glob("epoch_*.pt"))
    if epoch_ckpts:
        epoch_ckpts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return epoch_ckpts[0]
    
    return None


def run_yolo11s_training_v2(resume: bool = False):
    """Execute the YOLOv11s v2 training pipeline with resume support."""
    print("=" * 60)
    print("PYROGUARD YOLOv11s v2 MODEL TRAINING (960px)")
    print("=" * 60)
    print(f"Config: imgsz={TRAINING_CONFIG['image_size']}, batch={TRAINING_CONFIG['batch_size']}, "
          f"epochs={TRAINING_CONFIG['epochs']}, patience={TRAINING_CONFIG['patience']}")
    print()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("STAGE 1: Preparing dataset...")
    if not prepare_dataset_main():
        print("❌ Dataset preparation failed. Aborting.")
        return False
    print("✅ Dataset preparation complete")
    print()
    
    print("STAGE 2: Training YOLOv11s v2 model...")
    try:
        from ultralytics import YOLO
        import torch
        
        config = TRAINING_CONFIG
        final_model_path = PROJECT_ROOT / "models" / "fire_smoke_yolo11s_v2.pt"
        run_name = "yolo11s_fire_smoke_v2"
        
        device = config["device"]
        if not torch.cuda.is_available() and device == "cuda":
            device = "cpu"
            print("⚠️  CUDA not available, falling back to CPU")
        else:
            print(f"Using device: {device}")
        
        # Handle resume logic
        start_model = config["pretrained_weights"]
        resume_from = False
        
        if resume:
            latest_run = find_latest_run_dir(run_name)
            if latest_run:
                last_ckpt = get_last_checkpoint(latest_run)
                if last_ckpt:
                    print(f"📂 Resuming from checkpoint: {last_ckpt}")
                    start_model = str(last_ckpt)
                    resume_from = True
                else:
                    print("⚠️  No checkpoint found in latest run, starting fresh")
            else:
                print("⚠️  No previous run found, starting fresh")
        
        print(f"Loading weights: {start_model}")
        model = YOLO(start_model)
        
        print("Starting training...")
        print("Press Ctrl+C to stop and save checkpoint for resume later")
        print()
        
        train_args = {
            "data": str(PROJECT_ROOT / "datasets/processed/data.yaml"),
            "epochs": config["epochs"],
            "imgsz": config["image_size"],
            "batch": config["batch_size"],
            "lr0": config["learning_rate"],
            "optimizer": config["optimizer"],
            "device": device,
            "workers": config["workers"],
            "augment": config["augmentation"],
            "verbose": True,
            "name": run_name,
            "save_period": config["save_period"],
            "patience": config["patience"],
            "cos_lr": config["cosine_lr"],
            "warmup_epochs": config["warmup_epochs"],
            "warmup_momentum": config["warmup_momentum"],
            "warmup_bias_lr": config["warmup_bias_lr"],
            "amp": config["amp"],
        }
        
        if resume_from:
            train_args["resume"] = True
        
        results = model.train(**train_args)
        
        print(f"\n✅ Training complete. Best model saved to {results.save_dir}")
        print()
        
        best_model_path = Path(results.save_dir) / "weights" / "best.pt"
        
        if best_model_path.exists():
            shutil.copy2(str(best_model_path), str(final_model_path))
            print(f"✅ YOLOv11s v2 model saved to {final_model_path}")
        else:
            print(f"⚠️  Best model not found at expected path: {best_model_path}")
            return False
        
        print()
        print("=" * 60)
        print("YOLOv11s v2 TRAINING COMPLETE")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"❌ Required library not available: {e}")
        print("Install with: pip install ultralytics torch")
        return False
    except KeyboardInterrupt:
        print("\n⏸️  Training interrupted by user")
        print(f"To resume later, run: python scripts/train_v2.py --resume")
        return False
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv11s v2 (960px) for fire/smoke detection")
    parser.add_argument("--resume", action="store_true", 
                        help="Resume training from latest checkpoint")
    args = parser.parse_args()
    
    success = run_yolo11s_training_v2(resume=args.resume)
    exit(0 if success else 1)