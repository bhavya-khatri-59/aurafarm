"""Optional zero-shot check that a photo shows a plant, using CLIP (runs locally, no API calls).

The disease classifier always picks one of its 38 classes, even for a photo of a dog, so photos
that fail this check are answered with a fixed reply instead. Enable with LEAF_CHECK_ENABLED=true
and calibrate the threshold with `python -m scripts.check_leaf <photos>`.
"""

import asyncio
import logging
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageOps

from app.config import get_settings

logger = logging.getLogger(__name__)

PLANT_LABELS = [
    "a close-up photo of a plant leaf",
    "a photo of a diseased plant leaf with spots",
    "a photo of a plant or crop",
]
OTHER_LABELS = [
    "a photo of a person",
    "a photo of an animal",
    "a photo of food on a plate",
    "a photo of a building or a room",
    "a photo of a vehicle",
    "a photo of an everyday object",
    "a screenshot of a phone or computer screen",
    "a drawing, sketch or cartoon on paper",
    "a painting or illustration",
    "a photo of a document or text",
    "a plain single-colour background",
]


@lru_cache
def _load(model_name: str):
    from transformers import CLIPModel, CLIPProcessor

    model = CLIPModel.from_pretrained(model_name)
    model.eval()
    return model, CLIPProcessor.from_pretrained(model_name)


def plant_probability_sync(image_bytes: bytes) -> float:
    import torch

    model, processor = _load(get_settings().leaf_check_model)
    image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("RGB")
    inputs = processor(text=PLANT_LABELS + OTHER_LABELS, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        probabilities = model(**inputs).logits_per_image.softmax(dim=1)[0]
    return float(probabilities[: len(PLANT_LABELS)].sum())


async def plant_probability(image_bytes: bytes) -> float:
    return await asyncio.to_thread(plant_probability_sync, image_bytes)


async def looks_like_plant(image_bytes: bytes) -> bool:
    settings = get_settings()
    if not settings.leaf_check_enabled:
        return True
    probability = await plant_probability(image_bytes)
    logger.info("Leaf check: plant probability %.3f (threshold %.2f)", probability, settings.leaf_check_threshold)
    return probability >= settings.leaf_check_threshold
