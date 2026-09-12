#!/usr/bin/env python3
"""
PyroGuard Dataset Preparation Script
Inspects and validates the D-Fire dataset for YOLO training.

Requirements (from config):
- Inspect dataset structure
- Validate annotations
- Verify class names
- Detect corrupted images
- Detect missing annotations
- Detect duplicate images where practical
- Preserve predefined train/validation/test splits
- Do not modify the original dataset
- Create a separate processed dataset
"""

import os
import json
import cv2
from pathlib import Path
import shutil

# Dataset paths (D-Fire, do not modify originals)
RAW_DATASET_DIR = Path("datasets/raw")
PROCESSED_DATASET_DIR = Path("datasets/processed")

FIRE_CLASSES = ["fire", "smoke"]


def inspect_dataset_structure():
    """Inspect the dataset structure and print summary."""
    print("=" * 60)
    print("DATASET STRUCTURE INSPECTION")
    print("=" * 60)
    
    if not RAW_DATASET_DIR.exists():
        print(f"❌ Raw dataset directory not found: {RAW_DATASET_DIR}")
        return False
    
    # Check for YOLO structure: images/labels train/val/test
    splits = ["train", "val", "test"]
    valid_splits_found = []
    
    for split in splits:
        split_dir = RAW_DATASET_DIR / split
        if split_dir.exists():
            images_dir = split_dir / "images"
            labels_dir = split_dir / "labels"
            
            n_images = len(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))) if images_dir.exists() else 0
            n_labels = len(list(labels_dir.glob(".txt"))) if labels_dir.exists() else 0
            
            print(f"  {split}: {n_images} images, {n_labels} labels")
            valid_splits_found.append(split)
        else:
            print(f"  {split}: not found")
    
    print(f"\nValid splits: {valid_splits_found}")
    return len(valid_splits_found) > 0


def validate_annotations():
    """Validate annotation files for correctness."""
    print("\n" + "=" * 60)
    print("ANNOTATION VALIDATION")
    print("=" * 60)
    
    if not RAW_DATASET_DIR.exists():
        print(f"❌ Raw dataset directory not found: {RAW_DATASET_DIR}")
        return False
    
    splits = ["train", "val", "test"]
    valid = True
    
    for split in splits:
        split_dir = RAW_DATASET_DIR / split
        if not split_dir.exists():
            continue
        
        images_dir = split_dir / "images"
        labels_dir = split_dir / "labels"
        
        if not images_dir.exists() or not labels_dir.exists():
            print(f"  {split}: missing images/ or labels/ directory")
            valid = False
            continue
        
        image_files = list(images.glob("*.jpg") + list(images.glob("*.png")) for images in [images_dir])
        label_files = list(labels_dir.glob("*.txt"))
        
        # Check for missing labels
        image_stems = {f.stem for f in image_files}
        label_stems = {f.stem.replace(".txt", "") for f in label_files}  # labels are .txt
        
        missing_labels = image_stems - label_stems
        extra_labels = label_stems - image_stems
        
        if missing_labels:
            print(f"  {split}: {len(missing_labels)} images missing labels")
            valid = False
        
        if extra_labels:
            print(f"  {split}: {len(extra_labels)} label files without images")
            valid = False
        
        # Validate annotation content
        for label_file in label_files:
            try:
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) != 5:
                            print(f"  {split}: invalid annotation format in {label_file}: {line.strip()}")
                            valid = False
                            continue
                        
                        class_id, x_center, y_center, width, height = parts
                        try:
                            class_id = int(class_id)
                            if class_id < 0 or class_id >= len(FIRE_CLASSES):
                                print(f"  {split}: invalid class_id {class_id} in {label_file}")
                                valid = False
                        except ValueError:
                            print(f"  {split}: non-integer class_id in {label_file}")
                            valid = False
                        
                            # Check for out-of-range values (should be 0-1)
                            for val in [x_center, y_center, width, height]:
                                try:
                                    fval = float(val)
                                    if fval < 0 or fval > 1:
                                        print(f"  {split}: out-of-range coordinate {val} in {label_file}")
                                        valid = False
                                except ValueError:
                                    pass
            except Exception as e:
                print(f"  {split}: error reading {label_file}: {e}")
                valid = False
    
    print(f"\nAnnotations valid: {valid}")
    return valid


def verify_class_names():
    """Verify class names match expected classes."""
    print("\n" + "=" * 60)
    print("CLASS NAME VERIFICATION")
    print("=" * 60)
    
    # Collect all class IDs from annotations
    all_class_ids = set()
    
    for split in ["train", "val", "test"]:
        split_dir = RAW_DATASET_DIR / split
        if not split_dir.exists():
            continue
        
        labels_dir = split_dir / "labels"
        if not labels_dir.exists():
            continue
        
        for label_file in labels_dir.glob("*.txt"):
            try:
                with open(label_file, 'r') as f:
                    for line in f:
                        class_id = int(line.strip().split()[0])
                        all_class_ids.add(class_id)
            except Exception:
                pass
    
    print(f"  Found class IDs: {sorted(all_class_ids)}")
    print(f"  Expected classes: {FIRE_CLASSES}")
    
    # Map class IDs to names
    class_names = {i: FIRE_CLASSES[i] for i in range(len(FIRE_CLASSES)) if i in all_class_ids}
    print(f"  Active class names: {class_names}")
    
    valid = all_class_ids <= set(range(len(FIRE_CLASSES)))
    print(f"  Verification {'passed' if valid else 'failed'}")
    return valid


def detect_corrupted_images():
    """Detect corrupted or unreadable images."""
    print("\n" + "=" * 60)
    print("CORRUPTED IMAGE DETECTION")
    print("=" * 60)
    
    if not RAW_DATASET_DIR.exists():
        print(f"❌ Raw dataset directory not found: {RAW_DATASET_DIR}")
        return False
    
    corrupted = 0
    total = 0
    
    for split in ["train", "val", "test"]:
        split_dir = RAW_DATASET_DIR / split
        if not split_dir.exists():
            continue
        
        images_dir = split_dir / "images"
        if not images_dir.exists():
            continue
        
        for img_file in list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")):
            total += 1
            img = cv2.imread(str(img_file))
            if img is None:
                corrupted += 1
                print(f"  CORRUPTED: {img_file.name}")
    
    print(f"  Total images checked: {total}")
    print(f"  Corrupted images: {corrupted}")
    return corrupted == 0


def detect_missing_annotations():
    """Detect images missing corresponding annotation files."""
    print("\n" + "=" * 60)
    print("MISSING ANNOTATION DETECTION")
    print("=" * 60)
    
    if not RAW_DATASET_DIR.exists():
        print(f"❌ Raw dataset directory not found: {RAW_DATASET_DIR}")
        return False
    
    missing = 0
    total = 0
    
    for split in ["train", "val", "test"]:
        split_dir = RAW_DATASET_DIR / split
        if not split_dir.exists():
            continue
        
        images_dir = split_dir / "images"
        labels_dir = split_dir / "labels"
        
        if not images_dir.exists() or not labels_dir.exists():
            continue
        
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        
        for img_file in image_files:
            total += 1
            label_file = labels_dir / (img_file.stem + ".txt")
            if not label_file.exists():
                missing += 1
                print(f"  MISSING ANNOTATION: {img_file.name}")
    
    print(f"  Total images: {total}")
    print(f"  Missing annotations: {missing}")
    return missing == 0


def main():
    """Run all dataset validation checks."""
    print("PyroGuard Dataset Preparation")
    print(f"Raw dataset: {RAW_DATASET_DIR}")
    print(f"Processed dataset: {PROCESSED_DATASET_DIR}")
    print()
    
    results = {
        "structure": inspect_dataset_structure(),
        "annotations": validate_annotations(),
        "classes": verify_class_names(),
        "corrupted": detect_corrupted_images(),
        "missing_annotations": detect_missing_annotations()
    }
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")
    
    print(f"\nOverall: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")
    
    # Create processed directory structure if needed
    if all_passed:
        PROCESSED_DATASET_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nProcessed dataset directory ready: {PROCESSED_DATASET_DIR}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)