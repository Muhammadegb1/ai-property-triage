import torch
from torch.utils.data import DataLoader
from dataset import load_splits

train_ds, val_ds, test_ds = load_splits()

img, room_idx, cond_idx = train_ds[0]
print("Image tensor shape:", img.shape)
print("Room index        :", room_idx, "(0-5)")
print("Condition index   :", cond_idx, "(0-4)")

loader = DataLoader(train_ds, batch_size=4, shuffle=True)
imgs, rooms, conds = next(iter(loader))
print("Batch images      :", imgs.shape)
print("Batch rooms       :", rooms.tolist())
print("Batch conditions  :", conds.tolist())

assert img.shape == torch.Size([3, 224, 224])
assert 0 <= room_idx <= 5
assert 0 <= cond_idx <= 4
print("\nAll assertions passed.")
