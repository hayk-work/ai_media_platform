import uuid

from common.db import get_db_session
from common.models import MediaItem, User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user
from app.schemas import MediaItemResponse, MediaListResponse, ProcessingJobResponse

router = APIRouter(prefix="/media", tags=["media"])


def _to_media_response(item: MediaItem) -> MediaItemResponse:
    latest_job = None
    if item.processing_jobs:
        job = max(item.processing_jobs, key=lambda j: j.created_at)
        latest_job = ProcessingJobResponse(
            id=job.id,
            status=job.status,
            attempt_count=job.attempt_count,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    return MediaItemResponse(
        id=item.id,
        filename=item.filename,
        content_type=item.content_type,
        file_size_bytes=item.file_size_bytes,
        status=item.status,
        s3_key=item.s3_key,
        thumbnail_s3_key=item.thumbnail_s3_key,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
        latest_job=latest_job,
    )


@router.get("", response_model=MediaListResponse)
async def list_media(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MediaListResponse:
    result = await db.execute(
        select(MediaItem)
        .where(MediaItem.user_id == current_user.id)
        .options(selectinload(MediaItem.processing_jobs))
        .order_by(MediaItem.created_at.desc())
    )
    items = result.scalars().all()
    return MediaListResponse(items=[_to_media_response(item) for item in items])


@router.get("/{media_id}", response_model=MediaItemResponse)
async def get_media(
    media_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MediaItemResponse:
    result = await db.execute(
        select(MediaItem)
        .where(MediaItem.id == media_id, MediaItem.user_id == current_user.id)
        .options(selectinload(MediaItem.processing_jobs))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    return _to_media_response(item)
