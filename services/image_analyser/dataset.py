import os
import csv
from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_DIR  = os.path.join(DATA_DIR, "raw")

ROOM_TYPES  = [
    "balcony", "bathroom", "bedroom", "building_exterior",
    "garden", "kitchen_dining", "living_room", "not_real_estate",
]
ROOM_TO_IDX = {r: i for i, r in enumerate(ROOM_TYPES)}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

TRAIN_TRANSFORMS = transforms.Compose([
    transforms.Resize(256),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

VAL_TRANSFORMS = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


class PropertyImageDataset(Dataset):
    def __init__(self, rows: list, transform=None):
        self.rows = rows
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        img_path = os.path.join(RAW_DIR, row["filepath"])

        img = Image.open(img_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")

        if self.transform:
            img = self.transform(img)

        room_idx = ROOM_TO_IDX[row["room_type"]]
        cond_idx = int(row["condition_score"]) - 1  # 1-5 → 0-4

        return img, room_idx, cond_idx


def load_splits():
    csv_path = os.path.join(DATA_DIR, "labels.csv")

    train_rows, val_rows, test_rows = [], [], []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["split"] == "train":
                train_rows.append(r)
            elif r["split"] == "val":
                val_rows.append(r)
            else:
                test_rows.append(r)

    print(f"Split: train={len(train_rows)}  val={len(val_rows)}  test={len(test_rows)}")

    return (
        PropertyImageDataset(train_rows, transform=TRAIN_TRANSFORMS),
        PropertyImageDataset(val_rows,   transform=VAL_TRANSFORMS),
        PropertyImageDataset(test_rows,  transform=VAL_TRANSFORMS),
    )
