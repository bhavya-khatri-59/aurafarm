"""ResNet9 plant disease classifier (PlantVillage, 38 classes)."""

import asyncio
from io import BytesIO
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

from app.config import get_settings
from app.services.labels import CLASS_NAMES

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_transform = transforms.Compose([transforms.Resize((256, 256)), transforms.ToTensor()])


def _conv_block(in_channels: int, out_channels: int, pool: bool = False) -> nn.Sequential:
    layers = [
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    ]
    if pool:
        layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)


class ResNet9(nn.Module):
    def __init__(self, in_channels: int, num_classes: int):
        super().__init__()
        self.conv1 = _conv_block(in_channels, 64)
        self.conv2 = _conv_block(64, 128, pool=True)
        self.res1 = nn.Sequential(_conv_block(128, 128), _conv_block(128, 128))
        self.conv3 = _conv_block(128, 256, pool=True)
        self.conv4 = _conv_block(256, 512, pool=True)
        self.res2 = nn.Sequential(_conv_block(512, 512), _conv_block(512, 512))
        # AdaptiveMaxPool makes inference resolution-agnostic.
        self.classifier = nn.Sequential(
            nn.AdaptiveMaxPool2d(1), nn.Flatten(), nn.Linear(512, num_classes)
        )

    def forward(self, xb):
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        return self.classifier(out)


def _load_model(path: Path) -> nn.Module:
    if not path.exists():
        raise FileNotFoundError(f"Model weights not found at {path}")
    checkpoint = torch.load(path, map_location=_device, weights_only=False)
    if isinstance(checkpoint, nn.Module):
        model = checkpoint
    else:
        model = ResNet9(3, len(CLASS_NAMES))
        model.load_state_dict(checkpoint)
    model.to(_device)
    model.eval()
    return model


_model: nn.Module | None = None
_lock = asyncio.Lock()


async def _get_model() -> nn.Module:
    global _model
    if _model is None:
        async with _lock:
            if _model is None:
                _model = await asyncio.to_thread(_load_model, get_settings().model_path)
    return _model


def _predict_sync(model: nn.Module, image_bytes: bytes, top_k: int) -> list[tuple[str, float]]:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    tensor = _transform(image).unsqueeze(0).to(_device)
    with torch.no_grad():
        probabilities = F.softmax(model(tensor), dim=1)[0]
    values, indices = torch.topk(probabilities, k=top_k)
    return [(CLASS_NAMES[i], float(v)) for v, i in zip(values.tolist(), indices.tolist())]


async def predict(image_bytes: bytes, top_k: int = 3) -> list[tuple[str, float]]:
    """Returns the top-k (label, probability) pairs, most likely first."""
    model = await _get_model()
    return await asyncio.to_thread(_predict_sync, model, image_bytes, top_k)
