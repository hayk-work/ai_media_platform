
import structlog
from common.config import settings
from common.db import get_db_session
from common.enums import MediaStatus
from common.models import MediaItem, ProcessingJob, User
from common.s3 import build_media_object_key, generate_presigned_upload_url
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.schemas import UploadRequest, UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=UploadResponse)
async def create_upload_request(
    payload: UploadRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    logger.info(
        "upload_requested",
        user_id=str(current_user.id),
        filename=payload.filename,
        content_type=payload.content_type,
        file_size_bytes=payload.file_size_bytes,
    )

    media_item = MediaItem(
        user_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        file_size_bytes=payload.file_size_bytes,
        status=MediaStatus.UPLOADING,
    )
    db.add(media_item)
    await db.flush()

    s3_key = build_media_object_key(current_user.id, media_item.id, payload.filename)
    media_item.s3_key = s3_key

    processing_job = ProcessingJob(
        media_item_id=media_item.id,
        status=MediaStatus.UPLOADING,
    )
    db.add(processing_job)
    await db.commit()
    await db.refresh(media_item)

    upload_url: str | None = None
    if settings.s3_media_bucket:
        upload_url = generate_presigned_upload_url(
            bucket=settings.s3_media_bucket,
            object_key=s3_key,
            content_type=payload.content_type,
        )
        logger.info(
            "presigned_url_generated",
            media_id=str(media_item.id),
            user_id=str(current_user.id),
            s3_key=s3_key,
            bucket=settings.s3_media_bucket,
        )

    return UploadResponse(
        media_id=media_item.id,
        upload_url=upload_url,
        status=media_item.status,
    )
