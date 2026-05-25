"""
Fills condition_score for rows where score == 0 using image quality metrics.
Manually labeled rows (score != 0) are untouched.

Run:
    python services/image_analyser/data/auto_label.py
"""
import os
import csv
import numpy as np
from PIL import Image, ImageFilter, ImageStat

DATA_DIR   = os.path.dirname(__file__)
RAW_DIR    = os.path.join(DATA_DIR, "raw")
LABELS_CSV = os.path.join(DATA_DIR, "labels.csv")


def quality_score(img_path: str) -> float:
    try:
        img = Image.open(img_path).convert("RGB").resize((224, 224))
        gray = img.convert("L")

        stat = ImageStat.Stat(gray)
        brightness = stat.mean[0] / 255.0
        contrast   = min(stat.stddev[0] / 80.0, 1.0)

        edges     = gray.filter(ImageFilter.FIND_EDGES)
        sharpness = min(ImageStat.Stat(edges).mean[0] / 30.0, 1.0)

        r, g, b   = [np.array(ch, dtype=np.float32) for ch in img.split()]
        max_rgb   = np.maximum(np.maximum(r, g), b)
        min_rgb   = np.minimum(np.minimum(r, g), b)
        saturation = float(np.mean((max_rgb - min_rgb) / (max_rgb + 1e-6)))

        return 0.30 * brightness + 0.25 * sharpness + 0.25 * contrast + 0.20 * saturation
    except Exception:
        return 0.5


def main():
    rows = []
    with open(LABELS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    to_score = [r for r in rows if int(r["condition_score"]) == 0]
    print(f"Images to auto-label: {len(to_score)}")
    print(f"Already labeled:      {len(rows) - len(to_score)}\n")

    if not to_score:
        print("Nothing to label.")
        return

    print("Computing quality scores...")
    qs = [quality_score(os.path.join(RAW_DIR, r["filepath"])) for r in to_score]
    arr = np.array(qs)

    t1 = float(np.percentile(arr, 5))
    t2 = float(np.percentile(arr, 15))
    t3 = float(np.percentile(arr, 43))
    t4 = float(np.percentile(arr, 71))

    def score_from_quality(q):
        if q <= t1:   return 1
        elif q <= t2: return 2
        elif q <= t3: return 3
        elif q <= t4: return 4
        else:         return 5

    for r, q in zip(to_score, qs):
        r["condition_score"] = score_from_quality(q)

    fieldnames = list(rows[0].keys())
    with open(LABELS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    dist = Counter(int(r["condition_score"]) for r in rows)
    print(f"Updated {LABELS_CSV}\n")
    print("Final condition score distribution:")
    for s in sorted(dist):
        print(f"  Score {s}: {dist[s]}")


if __name__ == "__main__":
    main()
