import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from common.enums import MediaStatus, NotificationStatus
from common.models import ProcessingNotification, UserNotificationPreference
from common.sns import build_processing_notification_payload, publish_processing_notification

logger = structlog.get_logger(__name__)

COMPLETED_MESSAGE = "Your image is ready"
FAILED_MESSAGE = "Your image processing failed"


async def get_or_create_notification_preferences(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> UserNotificationPreference:
    preferences = await session.scalar(
        select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)
    )
    if preferences is not None:
        return preferences

    preferences = UserNotificationPreference(user_id=user_id)
    session.add(preferences)
    await session.commit()
    await session.refresh(preferences)
    return preferences


async def user_notifications_enabled(session: AsyncSession, user_id: uuid.UUID) -> bool:
    preferences = await get_or_create_notification_preferences(session, user_id)
    return preferences.email_enabled or preferences.sms_enabled


async def notify_processing_result(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    media_id: uuid.UUID,
    user_id: uuid.UUID,
    event_status: MediaStatus,
    message: str | None = None,
) -> ProcessingNotification | None:
    if event_status not in (MediaStatus.COMPLETED, MediaStatus.FAILED):
        return None

    if message is None:
        message = COMPLETED_MESSAGE if event_status == MediaStatus.COMPLETED else FAILED_MESSAGE

    async with session_factory() as session:
        if not await user_notifications_enabled(session, user_id):
            logger.info(
                "processing_notification_skipped",
                media_id=str(media_id),
                user_id=str(user_id),
                reason="notifications_disabled",
            )
            return None

        notification = ProcessingNotification(
            media_item_id=media_id,
            user_id=user_id,
            status=NotificationStatus.PENDING,
            event_status=event_status.value,
            message=message,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        notification_id = notification.id

    payload = build_processing_notification_payload(
        media_id=media_id,
        user_id=user_id,
        status=event_status.value,
        message=message,
    )

    try:
        sns_message_id = publish_processing_notification(payload)
        return await _mark_notification_sent(
            session_factory,
            notification_id=notification_id,
            sns_message_id=sns_message_id,
        )
    except Exception as exc:
        logger.exception(
            "processing_notification_failed",
            media_id=str(media_id),
            user_id=str(user_id),
            error=str(exc),
        )
        return await _mark_notification_failed(
            session_factory,
            notification_id=notification_id,
            error_message=str(exc),
        )


async def _mark_notification_sent(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    notification_id: uuid.UUID,
    sns_message_id: str,
) -> ProcessingNotification:
    async with session_factory() as session:
        notification = await session.get(ProcessingNotification, notification_id)
        if notification is None:
            raise RuntimeError(f"Notification {notification_id} disappeared")
        notification.status = NotificationStatus.SENT
        notification.sns_message_id = sns_message_id
        notification.error_message = None
        await session.commit()
        await session.refresh(notification)
        return notification


async def _mark_notification_failed(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    notification_id: uuid.UUID,
    error_message: str,
) -> ProcessingNotification:
    async with session_factory() as session:
        notification = await session.get(ProcessingNotification, notification_id)
        if notification is None:
            raise RuntimeError(f"Notification {notification_id} disappeared")
        notification.status = NotificationStatus.FAILED
        notification.error_message = error_message
        await session.commit()
        await session.refresh(notification)
        return notification
