"""
Extracts the teacher's zip, selects a balanced subset, and writes labels.csv.

Splits produced:
  train : TRAIN_PER_CLASS images per category  (from raw/train/)
  val   : VAL_PER_CLASS   images per category  (from raw/train/, different images)
  test  : TEST_PER_CLASS  images per category  (from raw/test/)

Run once:
    python services/image_analyser/data/prepare_dataset.py
"""
import os
import csv
import random
import zipfile
import shutil

import sys
ZIP_PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Muham\Downloads\training_dataset_v4_train_test.zip"
TRAIN_PER_CLASS = 400
VAL_PER_CLASS   = 40
TEST_PER_CLASS  = 40
SEED            = 42

CATEGORIES = [
    "balcony", "bathroom", "bedroom", "building_exterior",
    "garden", "kitchen_dining", "living_room", "not_real_estate",
]

DATA_DIR   = os.path.dirname(__file__)
RAW_DIR    = os.path.join(DATA_DIR, "raw")
LABELS_CSV = os.path.join(DATA_DIR, "labels.csv")


def extract_zip():
    if not os.path.exists(ZIP_PATH):
        raise FileNotFoundError(f"Zip not found: {ZIP_PATH}")
    if os.path.exists(RAW_DIR):
        shutil.rmtree(RAW_DIR)
    os.makedirs(RAW_DIR)
    print("Extracting zip...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(RAW_DIR)
    print("Done.\n")


def select_images(folder, n):
    """Return n image filenames from folder, delete the rest."""
    images = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ])
    random.seed(SEED)
    random.shuffle(images)
    kept   = images[:n]
    removed = images[n:]
    for f in removed:
        os.remove(os.path.join(folder, f))
    return kept


def main():
    extract_zip()

    rows = []

    # --- TRAIN + VAL from raw/train/ ---
    for cat in CATEGORIES:
        folder = os.path.join(RAW_DIR, "train", cat)
        if not os.path.exists(folder):
            print(f"WARNING: missing folder {folder}")
            continue

        needed = TRAIN_PER_CLASS + VAL_PER_CLASS
        images = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ])
        random.seed(SEED)
        random.shuffle(images)

        train_imgs = images[:TRAIN_PER_CLASS]
        val_imgs   = images[TRAIN_PER_CLASS:needed]
        remove     = images[needed:]

        for f in remove:
            os.remove(os.path.join(folder, f))

        for f in train_imgs:
            rows.append({"filepath": f"train/{cat}/{f}", "room_type": cat, "split": "train", "condition_score": 0})
        for f in val_imgs:
            rows.append({"filepath": f"train/{cat}/{f}", "room_type": cat, "split": "val", "condition_score": 0})

    # --- TEST from raw/test/ ---
    for cat in CATEGORIES:
        folder = os.path.join(RAW_DIR, "test", cat)
        if not os.path.exists(folder):
            print(f"WARNING: missing folder {folder}")
            continue

        images = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ])
        random.seed(SEED)
        random.shuffle(images)

        test_imgs = images[:TEST_PER_CLASS]
        remove    = images[TEST_PER_CLASS:]

        for f in remove:
            os.remove(os.path.join(folder, f))

        for f in test_imgs:
            rows.append({"filepath": f"test/{cat}/{f}", "room_type": cat, "split": "test", "condition_score": 0})

    # Write labels.csv
    fieldnames = ["filepath", "room_type", "split", "condition_score"]
    with open(LABELS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    train_n = sum(1 for r in rows if r["split"] == "train")
    val_n   = sum(1 for r in rows if r["split"] == "val")
    test_n  = sum(1 for r in rows if r["split"] == "test")

    print(f"labels.csv written: {len(rows)} rows")
    print(f"  train : {train_n} ({TRAIN_PER_CLASS} per class)")
    print(f"  val   : {val_n}   ({VAL_PER_CLASS} per class)")
    print(f"  test  : {test_n}  ({TEST_PER_CLASS} per class)")


if __name__ == "__main__":
    main()
