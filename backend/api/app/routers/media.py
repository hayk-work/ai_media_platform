import uuid

from common.db import get_db_session
from common.enums import AiAnalysisStatus
from common.models import MediaAiResult, MediaItem, User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user
from app.schemas import (
    MediaAiResultResponse,
    MediaItemResponse,
    MediaListResponse,
    ProcessingJobResponse,
)

router = APIRouter(prefix="/media", tags=["media"])


def _to_ai_response(ai_result: MediaAiResult) -> MediaAiResultResponse:
    return MediaAiResultResponse(
        id=ai_result.id,
        caption=ai_result.caption,
        tags=ai_result.tags,
        labels=ai_result.labels,
        quality_issues=ai_result.quality_issues,
        is_safe=ai_result.is_safe,
        provider=ai_result.provider,
        model=ai_result.model,
        status=ai_result.status,
        error_message=ai_result.error_message,
        created_at=ai_result.created_at,
        updated_at=ai_result.updated_at,
    )


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

    ai_result = None
    if item.ai_result is not None:
        ai_result = _to_ai_response(item.ai_result)

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
        ai_result=ai_result,
    )


def _media_query_options():
    return (
        selectinload(MediaItem.processing_jobs),
        selectinload(MediaItem.ai_result),
    )


@router.get("", response_model=MediaListResponse)
async def list_media(
    tag: str | None = Query(default=None, min_length=1, max_length=128),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> MediaListResponse:
    stmt = (
        select(MediaItem)
        .where(MediaItem.user_id == current_user.id)
        .options(*_media_query_options())
        .order_by(MediaItem.created_at.desc())
    )
    if tag is not None:
        normalized_tag = tag.strip().lower()
        stmt = (
            select(MediaItem)
            .join(MediaAiResult)
            .where(
                MediaItem.user_id == current_user.id,
                MediaAiResult.status == AiAnalysisStatus.COMPLETED,
                MediaAiResult.tags.contains([normalized_tag]),
            )
            .options(*_media_query_options())
            .order_by(MediaItem.created_at.desc())
        )

    result = await db.execute(stmt)
    items = result.scalars().unique().all()
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
        .options(*_media_query_options())
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    return _to_media_response(item)
