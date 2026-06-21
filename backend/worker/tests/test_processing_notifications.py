import uuid
from unittest.mock import patch

import pytest
from common.db import async_session_factory
from common.enums import MediaStatus, NotificationStatus
from common.models import ProcessingNotification, User, UserNotificationPreference
from common.notifications import (
    get_or_create_notification_preferences,
    notify_processing_result,
)
from common.security import hash_password
from sqlalchemy import select


@pytest.mark.asyncio
async def test_get_or_create_notification_preferences_creates_defaults(db_available) -> None:
    user_id = uuid.uuid4()
    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"prefs-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        await session.commit()

    async with async_session_factory() as session:
        preferences = await get_or_create_notification_preferences(session, user_id)

    assert preferences.email_enabled is True
    assert preferences.sms_enabled is False


@pytest.mark.asyncio
async def test_notify_processing_result_persists_sent_notification(db_available) -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"notify-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        from common.models import MediaItem

        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="notify.jpg",
                content_type="image/jpeg",
                file_size_bytes=100,
                status=MediaStatus.COMPLETED,
            )
        )
        await session.commit()

    with patch(
        "common.notifications.publish_processing_notification",
        return_value="sns-message-123",
    ):
        notification = await notify_processing_result(
            async_session_factory,
            media_id=media_id,
            user_id=user_id,
            event_status=MediaStatus.COMPLETED,
        )

    assert notification is not None
    assert notification.status == NotificationStatus.SENT
    assert notification.event_status == "COMPLETED"
    assert notification.message == "Your image is ready"
    assert notification.sns_message_id == "sns-message-123"

    async with async_session_factory() as session:
        stored = await session.scalar(
            select(ProcessingNotification).where(ProcessingNotification.id == notification.id)
        )
    assert stored is not None
    assert stored.status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_notify_processing_result_marks_failed_on_publish_error(db_available) -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"notify-fail-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        from common.models import MediaItem

        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="notify-fail.jpg",
                content_type="image/jpeg",
                file_size_bytes=100,
                status=MediaStatus.FAILED,
            )
        )
        await session.commit()

    with patch(
        "common.notifications.publish_processing_notification",
        side_effect=RuntimeError("sns unavailable"),
    ):
        notification = await notify_processing_result(
            async_session_factory,
            media_id=media_id,
            user_id=user_id,
            event_status=MediaStatus.FAILED,
        )

    assert notification is not None
    assert notification.status == NotificationStatus.FAILED
    assert notification.event_status == "FAILED"
    assert notification.error_message == "sns unavailable"


@pytest.mark.asyncio
async def test_notify_processing_result_skips_when_disabled(db_available) -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"notify-skip-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        session.add(
            UserNotificationPreference(
                user_id=user_id,
                email_enabled=False,
                sms_enabled=False,
            )
        )
        from common.models import MediaItem

        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="skip.jpg",
                content_type="image/jpeg",
                file_size_bytes=100,
                status=MediaStatus.COMPLETED,
            )
        )
        await session.commit()

    notification = await notify_processing_result(
        async_session_factory,
        media_id=media_id,
        user_id=user_id,
        event_status=MediaStatus.COMPLETED,
    )
    assert notification is None

    async with async_session_factory() as session:
        stored = list(
            (await session.scalars(select(ProcessingNotification))).all()
        )
    assert stored == []
