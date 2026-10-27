"""Persistent caches that keep repeat photos and known diseases off the LLM API.

Photos are matched by a perceptual hash rather than a byte hash: the phone's image picker
re-compresses photos, so the same picture rarely arrives as the same bytes twice.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image, ImageOps
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import RemedyCache, ResponseCache


def image_hash(image_bytes: bytes) -> str:
    """64-bit difference hash (dHash) as 16 hex chars; stable across re-encoding and resizing."""
    image = ImageOps.exif_transpose(Image.open(BytesIO(image_bytes))).convert("L").resize((9, 8), Image.LANCZOS)
    pixels = image.tobytes()  # one byte per pixel in "L" mode
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (pixels[row * 9 + col] < pixels[row * 9 + col + 1])
    return f"{bits:016x}"


def hash_distance(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


async def find_response(session: AsyncSession, photo_hash: str, text: str | None) -> ResponseCache | None:
    """Closest cached reply to this photo. With `text=None` any text matches (demo mode);
    otherwise the normalized text must match too."""
    max_distance = get_settings().image_match_distance
    query = select(ResponseCache).order_by(ResponseCache.created_at.desc())
    if text is not None:
        query = query.where(ResponseCache.text == normalize_text(text))
    best, best_distance = None, max_distance + 1
    for entry in (await session.scalars(query)).all():
        distance = hash_distance(photo_hash, entry.image_hash)
        if distance < best_distance:
            best, best_distance = entry, distance
    return best


async def store_response(
    session: AsyncSession, photo_hash: str, text: str, reply: str, diagnosis: dict | None, remedy_notes: str | None
) -> None:
    normalized = normalize_text(text)
    await session.execute(
        delete(ResponseCache).where(ResponseCache.image_hash == photo_hash, ResponseCache.text == normalized)
    )
    session.add(
        ResponseCache(image_hash=photo_hash, text=normalized, reply=reply, diagnosis=diagnosis, remedy_notes=remedy_notes)
    )
    await session.commit()


async def get_remedy_notes(session: AsyncSession, label: str) -> str | None:
    entry = await session.get(RemedyCache, label)
    if entry is None:
        return None
    created = entry.created_at if entry.created_at.tzinfo else entry.created_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(days=get_settings().remedy_cache_days):
        return None
    return entry.notes


async def store_remedy_notes(session: AsyncSession, label: str, notes: str) -> None:
    await session.merge(RemedyCache(label=label, notes=notes, created_at=datetime.now(timezone.utc)))
    await session.commit()
