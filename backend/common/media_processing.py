import uuid
from dataclasses import dataclass
from io import BytesIO

import structlog
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common.config import settings
from common.enums import MediaStatus
from common.models import MediaItem, ProcessingJob
from common.s3 import build_thumbnail_object_key, download_object_bytes, upload_object_bytes

logger = structlog.get_logger(__name__)

THUMBNAIL_MAX_SIZE = (256, 256)


@dataclass(frozen=True)
class UploadObjectRef:
    user_id: uuid.UUID
    media_id: uuid.UUID
    filename: str


def parse_upload_object_key(object_key: str) -> UploadObjectRef | None:
    parts = object_key.split("/")
    if len(parts) < 4 or parts[0] != "uploads":
        return None
    try:
        return UploadObjectRef(
            user_id=uuid.UUID(parts[1]),
            media_id=uuid.UUID(parts[2]),
            filename="/".join(parts[3:]),
        )
    except ValueError:
        return None


def create_thumbnail_image(content: bytes) -> tuple[bytes, dict]:
    with Image.open(BytesIO(content)) as image:
        image = image.convert("RGB")
        width, height = image.size
        image.thumbnail(THUMBNAIL_MAX_SIZE)
        output = BytesIO()
        image.save(output, format="JPEG", quality=85)
        metadata = {
            "original_width": width,
            "original_height": height,
            "thumbnail_width": image.width,
            "thumbnail_height": image.height,
        }
        return output.getvalue(), metadata


async def mark_media_processing(session: AsyncSession, media_id: uuid.UUID) -> MediaItem | None:
    result = await session.execute(
        update(MediaItem)
        .where(
            MediaItem.id == media_id,
            MediaItem.status.in_([MediaStatus.UPLOADING]),
        )
        .values(status=MediaStatus.PROCESSING)
        .returning(MediaItem)
    )
    media_item = result.scalar_one_or_none()
    if media_item is not None:
        await session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.media_item_id == media_id)
            .values(status=MediaStatus.PROCESSING)
        )
        await session.commit()
        return media_item

    existing = await session.scalar(select(MediaItem).where(MediaItem.id == media_id))
    await session.rollback()
    return None


async def mark_media_completed(
    session: AsyncSession,
    media_item: MediaItem,
    *,
    thumbnail_key: str,
    metadata: dict,
) -> None:
    media_item.status = MediaStatus.COMPLETED
    media_item.thumbnail_s3_key = thumbnail_key
    media_item.metadata_json = metadata
    await session.execute(
        update(ProcessingJob)
        .where(ProcessingJob.media_item_id == media_item.id)
        .values(status=MediaStatus.COMPLETED, error_message=None)
    )
    await session.commit()


async def run_ai_analysis_for_media(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    media_id: uuid.UUID,
    filename: str,
    content_type: str,
    image_bytes: bytes,
) -> None:
    from common.ai.persistence import persist_ai_failure, persist_ai_success
    from common.ai.workflow import load_context, run_media_analysis_workflow

    if not settings.ai_enabled:
        logger.info("ai_analysis_skipped", media_id=str(media_id), reason="ai_disabled")
        return

    context = load_context(
        {
            "filename": filename,
            "content_type": content_type,
            "image_bytes": image_bytes,
        }
    )
    provider = context["provider"]
    model = context["model"]

    logger.info("ai_analysis_started", media_id=str(media_id), provider=provider, model=model)
    try:
        analysis = run_media_analysis_workflow(
            filename=filename,
            content_type=content_type,
            image_bytes=image_bytes,
        )
        await persist_ai_success(
            session_factory,
            media_item_id=media_id,
            analysis=analysis,
            provider=provider,
            model=model,
        )
        logger.info("ai_analysis_completed", media_id=str(media_id))
    except Exception as exc:
        logger.exception("ai_analysis_failed", media_id=str(media_id), error=str(exc))
        await persist_ai_failure(
            session_factory,
            media_item_id=media_id,
            error_message=str(exc),
            provider=provider,
            model=model,
        )


async def mark_media_failed(
    session: AsyncSession,
    media_id: uuid.UUID,
    error_message: str,
) -> None:
    await session.execute(
        update(MediaItem)
        .where(MediaItem.id == media_id)
        .values(status=MediaStatus.FAILED)
    )
    await session.execute(
        update(ProcessingJob)
        .where(ProcessingJob.media_item_id == media_id)
        .values(status=MediaStatus.FAILED, error_message=error_message)
    )
    await session.commit()


async def process_upload_object(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    bucket: str,
    object_key: str,
) -> bool:
    ref = parse_upload_object_key(object_key)
    if ref is None:
        logger.warning("unsupported_object_key", object_key=object_key)
        return True

    async with session_factory() as session:
        media_item = await mark_media_processing(session, ref.media_id)
        if media_item is None:
            logger.info("processing_skipped_idempotent", media_id=str(ref.media_id))
            return True

    logger.info(
        "processing_started",
        media_id=str(ref.media_id),
        object_key=object_key,
    )

    try:
        original_bytes = download_object_bytes(bucket=bucket, object_key=object_key)
        thumbnail_bytes, metadata = create_thumbnail_image(original_bytes)
        thumbnail_key = build_thumbnail_object_key(ref.user_id, ref.media_id, ref.filename)
        upload_object_bytes(
            bucket=bucket,
            object_key=thumbnail_key,
            body=thumbnail_bytes,
            content_type="image/jpeg",
        )

        async with session_factory() as session:
            media_item = await session.get(MediaItem, ref.media_id)
            if media_item is None:
                raise RuntimeError(f"Media item {ref.media_id} disappeared during processing")
            await mark_media_completed(
                session,
                media_item,
                thumbnail_key=thumbnail_key,
                metadata=metadata,
            )
            content_type = media_item.content_type
            filename = media_item.filename

        logger.info(
            "processing_completed",
            media_id=str(ref.media_id),
            thumbnail_key=thumbnail_key,
        )

        await run_ai_analysis_for_media(
            session_factory,
            media_id=ref.media_id,
            filename=filename,
            content_type=content_type,
            image_bytes=original_bytes,
        )
        return True
    except Exception as exc:
        logger.exception("processing_failed", media_id=str(ref.media_id), error=str(exc))
        async with session_factory() as session:
            await mark_media_failed(session, ref.media_id, str(exc))
        return False
