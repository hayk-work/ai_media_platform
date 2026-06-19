from common.db import get_db_session
from common.enums import MediaStatus
from common.models import MediaItem, ProcessingJob, User
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.schemas import UploadRequest, UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse)
async def create_upload_request(
    payload: UploadRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    media_item = MediaItem(
        user_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        file_size_bytes=payload.file_size_bytes,
        status=MediaStatus.UPLOADING,
    )
    db.add(media_item)
    await db.flush()

    processing_job = ProcessingJob(
        media_item_id=media_item.id,
        status=MediaStatus.UPLOADING,
    )
    db.add(processing_job)
    await db.commit()
    await db.refresh(media_item)

    return UploadResponse(media_id=media_item.id, status=media_item.status)
