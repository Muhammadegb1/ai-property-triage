import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

NUM_ROOM_TYPES = 6
NUM_CONDITION_SCORES = 5
FEATURE_DIM = 1280  # EfficientNet-B0 output features


class PropertyImageModel(nn.Module):
    def __init__(self):
        super().__init__()

        base = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)

        # Frozen backbone
        self.features = base.features
        self.avgpool = base.avgpool
        for param in self.features.parameters():
            param.requires_grad = False

        # Dual heads — trained from scratch
        self.room_head = nn.Linear(FEATURE_DIM, NUM_ROOM_TYPES)
        self.condition_head = nn.Linear(FEATURE_DIM, NUM_CONDITION_SCORES)

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        return self.room_head(x), self.condition_head(x)
