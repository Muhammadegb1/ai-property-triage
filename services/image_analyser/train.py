import os
import csv
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from dataset import load_splits, DATA_DIR
from model import PropertyImageModel

CHECKPOINTS_DIR     = os.path.join(os.path.dirname(__file__), "checkpoints")
os.makedirs(CHECKPOINTS_DIR, exist_ok=True)

EPOCHS              = 20
BATCH_SIZE          = 16
LR                  = 1e-3
CONDITION_WEIGHT    = 0.5
EARLY_STOP_PATIENCE = 5
DEVICE              = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def accuracy(logits, targets):
    return (logits.argmax(dim=1) == targets).float().mean().item()


def make_balanced_sampler(train_ds):
    # Read condition scores directly from labels.csv — faster than loading images
    csv_path = os.path.join(DATA_DIR, "labels.csv")
    filepath_to_cond = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            filepath_to_cond[r["filepath"]] = int(r["condition_score"]) - 1

    condition_counts = [0] * 5
    for row in train_ds.rows:
        cond_idx = filepath_to_cond[row["filepath"]]
        condition_counts[cond_idx] += 1

    print(f"Condition class counts in train: {condition_counts}")

    sample_weights = []
    for row in train_ds.rows:
        cond_idx = filepath_to_cond[row["filepath"]]
        sample_weights.append(1.0 / max(condition_counts[cond_idx], 1))

    return WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(train_ds),
        replacement=True,
    )


def run_epoch(model, loader, criterion_room, criterion_cond, optimizer=None):
    training = optimizer is not None
    model.train() if training else model.eval()

    total_loss, room_acc, cond_acc, n = 0.0, 0.0, 0.0, 0

    with torch.set_grad_enabled(training):
        for imgs, rooms, conds in loader:
            imgs  = imgs.to(DEVICE)
            rooms = rooms.to(DEVICE)
            conds = conds.to(DEVICE)

            room_logits, cond_logits = model(imgs)
            loss = criterion_room(room_logits, rooms) + CONDITION_WEIGHT * criterion_cond(cond_logits, conds)

            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            b = imgs.size(0)
            total_loss += loss.item() * b
            room_acc   += accuracy(room_logits, rooms) * b
            cond_acc   += accuracy(cond_logits, conds) * b
            n          += b

    return total_loss / n, room_acc / n, cond_acc / n


def main():
    print(f"Device: {DEVICE}\n")

    train_ds, val_ds, test_ds = load_splits()

    train_sampler = make_balanced_sampler(train_ds)
    train_loader  = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    val_loader    = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader   = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model          = PropertyImageModel().to(DEVICE)
    criterion_room = nn.CrossEntropyLoss()
    criterion_cond = nn.CrossEntropyLoss()
    optimizer      = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=LR
    )

    best_val_room_acc       = 0.0
    best_epoch              = 0
    epochs_since_improvement = 0

    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_room, tr_cond = run_epoch(model, train_loader, criterion_room, criterion_cond, optimizer)
        vl_loss, vl_room, vl_cond = run_epoch(model, val_loader,   criterion_room, criterion_cond)

        marker = ""
        if vl_room > best_val_room_acc:
            best_val_room_acc        = vl_room
            best_epoch               = epoch
            epochs_since_improvement = 0
            torch.save(model.state_dict(), os.path.join(CHECKPOINTS_DIR, "best_model.pth"))
            marker = " <-- saved"
        else:
            epochs_since_improvement += 1

        print(
            f"Epoch {epoch:02d}/{EPOCHS} | "
            f"Loss {tr_loss:.3f}/{vl_loss:.3f} | "
            f"Room {tr_room*100:.1f}%/{vl_room*100:.1f}% | "
            f"Cond {tr_cond*100:.1f}%/{vl_cond*100:.1f}%"
            f"{marker}"
        )

        if epochs_since_improvement >= EARLY_STOP_PATIENCE:
            print(f"\nEarly stopping at epoch {epoch} — no improvement for {EARLY_STOP_PATIENCE} epochs.")
            break

    if best_val_room_acc < 0.55:
        print("\nVal accuracy below 55% — unfreezing last backbone block...")
        for param in model.features[-1].parameters():
            param.requires_grad = True
        optimizer = torch.optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4
        )
        for epoch in range(EPOCHS + 1, EPOCHS + 6):
            tr_loss, tr_room, tr_cond = run_epoch(model, train_loader, criterion_room, criterion_cond, optimizer)
            vl_loss, vl_room, vl_cond = run_epoch(model, val_loader,   criterion_room, criterion_cond)

            marker = ""
            if vl_room > best_val_room_acc:
                best_val_room_acc = vl_room
                best_epoch        = epoch
                torch.save(model.state_dict(), os.path.join(CHECKPOINTS_DIR, "best_model.pth"))
                marker = " <-- saved"

            print(
                f"Epoch {epoch:02d} (FT) | "
                f"Loss {tr_loss:.3f}/{vl_loss:.3f} | "
                f"Room {tr_room*100:.1f}%/{vl_room*100:.1f}% | "
                f"Cond {tr_cond*100:.1f}%/{vl_cond*100:.1f}%"
                f"{marker}"
            )

    model.load_state_dict(torch.load(os.path.join(CHECKPOINTS_DIR, "best_model.pth"), map_location=DEVICE))
    _, test_room, test_cond = run_epoch(model, test_loader, criterion_room, criterion_cond)

    report = (
        f"\n{'='*50}\n"
        f"Best checkpoint: epoch {best_epoch}\n"
        f"=== Final Test Set Results ===\n"
        f"Room Type Accuracy : {test_room*100:.1f}%\n"
        f"Condition Accuracy : {test_cond*100:.1f}%\n"
        f"{'='*50}\n"
    )
    print(report)

    with open(os.path.join(CHECKPOINTS_DIR, "training_report.txt"), "w") as f:
        f.write(report)
    print(f"Report saved to checkpoints/training_report.txt")


if __name__ == "__main__":
    main()
