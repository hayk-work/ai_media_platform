import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common.ai.schemas import MediaAnalysisOutput
from common.enums import AiAnalysisStatus
from common.models import MediaAiResult

logger = structlog.get_logger(__name__)


async def get_or_create_ai_result(
    session: AsyncSession, media_item_id: uuid.UUID
) -> MediaAiResult:
    existing = await session.scalar(
        select(MediaAiResult).where(MediaAiResult.media_item_id == media_item_id)
    )
    if existing is not None:
        return existing

    ai_result = MediaAiResult(
        media_item_id=media_item_id,
        status=AiAnalysisStatus.PENDING,
        tags=[],
        labels=[],
        quality_issues=[],
    )
    session.add(ai_result)
    await session.flush()
    return ai_result


async def persist_ai_success(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    media_item_id: uuid.UUID,
    analysis: MediaAnalysisOutput,
    provider: str,
    model: str,
) -> None:
    async with session_factory() as session:
        ai_result = await get_or_create_ai_result(session, media_item_id)
        ai_result.caption = analysis.caption
        ai_result.tags = analysis.tags
        ai_result.labels = analysis.labels
        ai_result.quality_issues = analysis.quality_issues
        ai_result.is_safe = analysis.is_safe
        ai_result.provider = provider
        ai_result.model = model
        ai_result.status = AiAnalysisStatus.COMPLETED
        ai_result.error_message = None
        await session.commit()

    logger.info(
        "ai_result_persisted",
        media_id=str(media_item_id),
        status=AiAnalysisStatus.COMPLETED.value,
        tag_count=len(analysis.tags),
    )


async def persist_ai_failure(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    media_item_id: uuid.UUID,
    error_message: str,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    async with session_factory() as session:
        ai_result = await get_or_create_ai_result(session, media_item_id)
        ai_result.status = AiAnalysisStatus.FAILED
        ai_result.error_message = error_message
        ai_result.provider = provider
        ai_result.model = model
        await session.commit()

    logger.warning(
        "ai_result_failed",
        media_id=str(media_item_id),
        status=AiAnalysisStatus.FAILED.value,
        error=error_message,
    )
