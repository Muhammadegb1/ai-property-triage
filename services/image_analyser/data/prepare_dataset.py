"""
Extracts the dataset zip into raw/, rebuilds labels.csv.
"""
import os
import csv
import shutil
import zipfile
from collections import Counter

ZIP_PATH = r"C:\Users\Muham\Downloads\training_dataset_v4_train_test.zip"
DATA_DIR = os.path.dirname(__file__)
RAW_DIR  = os.path.join(DATA_DIR, "raw")
LABELS   = os.path.join(DATA_DIR, "labels.csv")

OLD_FOLDERS = ["kitchen", "bathroom", "living_room", "bedroom", "exterior", "other"]

CATEGORIES = {
    "balcony", "bathroom", "bedroom", "building_exterior",
    "garden", "kitchen_dining", "living_room", "not_real_estate",
}


def main():
    # Remove old Kaggle folders
    print("Removing old folders...")
    for folder in OLD_FOLDERS:
        path = os.path.join(RAW_DIR, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"  Deleted: {folder}/")

    # Extract teacher's dataset
    print("\nExtracting dataset...")
    rows = []
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        entries = [e for e in zf.namelist() if not e.endswith("/")]
        for i, name in enumerate(entries):
            parts = name.split("/")
            if len(parts) != 3:
                continue
            split, category, fname = parts
            if split not in ("train", "test") or category not in CATEGORIES:
                continue

            dest_dir = os.path.join(RAW_DIR, split, category)
            os.makedirs(dest_dir, exist_ok=True)

            with zf.open(name) as src, open(os.path.join(dest_dir, fname), "wb") as dst:
                dst.write(src.read())

            rows.append({
                "filepath":        f"{split}/{category}/{fname}",
                "room_type":       category,
                "split":           split,
                "condition_score": 0,
            })

            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{len(entries)} files extracted...")

    # Write labels.csv
    with open(LABELS, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filepath", "room_type", "split", "condition_score"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nTotal images: {len(rows)}")
    print("\nPer split:")
    for s, c in sorted(Counter(r["split"] for r in rows).items()):
        print(f"  {s}: {c}")
    print("\nPer category:")
    for cat, c in sorted(Counter(r["room_type"] for r in rows).items()):
        print(f"  {cat}: {c}")
    print("\nDone. Run auto_label.py next.")


if __name__ == "__main__":
    main()
