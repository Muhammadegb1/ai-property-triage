from contextlib import asynccontextmanager
from io import BytesIO
import os

import requests
import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from PIL import Image, ImageOps
from pydantic import BaseModel
from torchvision import transforms

from model import PropertyImageModel
from dataset import ROOM_TYPES, IMAGENET_MEAN, IMAGENET_STD

CHECKPOINT_PATH      = os.path.join(os.path.dirname(__file__), "checkpoints", "best_model.pth")
CONFIDENCE_THRESHOLD = float(os.getenv("IMAGE_CONFIDENCE_THRESHOLD", "0.6"))
DEVICE               = torch.device("cpu")

INFERENCE_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT_PATH}")
    model = PropertyImageModel().to(DEVICE)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE))
    model.eval()
    print(f"Model loaded from {CHECKPOINT_PATH}")
    yield


app = FastAPI(lifespan=lifespan)


class AnalyseRequest(BaseModel):
    image_url: str


class AnalyseResponse(BaseModel):
    room_type: str
    condition_score: int
    confidence: float


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/analyse", response_model=AnalyseResponse)
def analyse(req: AnalyseRequest):
    try:
        resp = requests.get(req.image_url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
    except requests.RequestException as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch image: {e}")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not decode image")

    try:
        img = ImageOps.exif_transpose(img).convert("RGB")
        tensor = INFERENCE_TRANSFORM(img).unsqueeze(0).to(DEVICE)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not process image")

    with torch.no_grad():
        room_logits, cond_logits = model(tensor)

    room_probs = F.softmax(room_logits, dim=1)[0]
    cond_probs = F.softmax(cond_logits, dim=1)[0]

    room_conf = float(room_probs.max())
    room_idx  = int(room_probs.argmax())
    cond_idx  = int(cond_probs.argmax())

    room_type       = "uncertain" if room_conf < CONFIDENCE_THRESHOLD else ROOM_TYPES[room_idx]
    condition_score = cond_idx + 1  # 0-4 → 1-5

    return AnalyseResponse(
        room_type=room_type,
        condition_score=condition_score,
        confidence=round(room_conf, 3),
    )
