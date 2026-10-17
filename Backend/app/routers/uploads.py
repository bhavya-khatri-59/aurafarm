from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import Upload, User, _uuid
from app.schemas import UploadOut
from app.security import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def upload_path(upload: Upload) -> Path:
    return get_settings().uploads_dir / upload.filename


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def create_upload(
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    extension = _EXTENSIONS.get(image.content_type or "")
    if extension is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a JPEG, PNG or WebP image")
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Images must be 10 MB or smaller")

    upload_id = _uuid()
    upload = Upload(id=upload_id, user_id=user.id, filename=f"{upload_id}{extension}",
                    content_type=image.content_type)
    path = upload_path(upload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    session.add(upload)
    await session.commit()
    return UploadOut(id=upload_id)


@router.get("/{upload_id}")
async def get_upload(
    upload_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    upload = await session.get(Upload, upload_id)
    if upload is None or upload.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return FileResponse(upload_path(upload), media_type=upload.content_type)
