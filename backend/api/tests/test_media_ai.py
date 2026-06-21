import uuid
from io import BytesIO

import pytest
from app.main import app
from common.config import settings
from common.db import async_session_factory, engine
from common.enums import AiAnalysisStatus, MediaStatus
from common.models import MediaAiResult, MediaItem, User
from common.security import hash_password
from httpx import ASGITransport, AsyncClient
from PIL import Image


def _sample_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color="green")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_list_media_filter_by_ai_tag(db_available) -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    ai_result_id = uuid.uuid4()

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"media-ai-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="tagged.jpg",
                content_type="image/jpeg",
                file_size_bytes=1024,
                status=MediaStatus.COMPLETED,
            )
        )
        session.add(
            MediaAiResult(
                id=ai_result_id,
                media_item_id=media_id,
                caption="A green test image.",
                tags=["mock", "portfolio", "green"],
                labels=["photo"],
                quality_issues=[],
                is_safe=True,
                provider="mock",
                model="mock-analysis",
                status=AiAnalysisStatus.COMPLETED,
            )
        )
        await session.commit()

    from app.dependencies import get_current_user

    fake_user = type("User", (), {"id": user_id})()

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        matched = await client.get("/media?tag=green", headers={"Authorization": "Bearer test"})
        unmatched = await client.get("/media?tag=ocean", headers={"Authorization": "Bearer test"})
        detail = await client.get(f"/media/{media_id}", headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    assert matched.status_code == 200
    matched_items = matched.json()["items"]
    assert len(matched_items) == 1
    assert matched_items[0]["id"] == str(media_id)
    assert matched_items[0]["ai_result"]["tags"] == ["mock", "portfolio", "green"]

    assert unmatched.status_code == 200
    assert unmatched.json()["items"] == []

    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["ai_result"]["caption"] == "A green test image."
    assert detail_payload["ai_result"]["status"] == AiAnalysisStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_process_upload_persists_mock_ai_result(
    db_available, monkeypatch: pytest.MonkeyPatch
) -> None:
    import boto3
    from common.media_processing import process_upload_object
    from common.s3 import build_media_object_key, upload_object_bytes
    from moto import mock_aws

    monkeypatch.setattr(settings, "ai_mock_mode", True)
    monkeypatch.setattr(settings, "groq_api_key", "")

    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    filename = "workflow.jpg"
    bucket = "ai-processing-test-bucket"
    object_key = build_media_object_key(user_id, media_id, filename)

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"worker-ai-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename=filename,
                content_type="image/jpeg",
                file_size_bytes=len(_sample_jpeg_bytes()),
                status=MediaStatus.UPLOADING,
                s3_key=object_key,
            )
        )
        from common.models import ProcessingJob

        session.add(
            ProcessingJob(
                media_item_id=media_id,
                status=MediaStatus.UPLOADING,
            )
        )
        await session.commit()

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=bucket)
        upload_object_bytes(
            bucket=bucket,
            object_key=object_key,
            body=_sample_jpeg_bytes(),
            content_type="image/jpeg",
        )

        success = await process_upload_object(
            async_session_factory,
            bucket=bucket,
            object_key=object_key,
        )

    assert success is True

    async with async_session_factory() as session:
        from sqlalchemy import select

        media_item = await session.scalar(select(MediaItem).where(MediaItem.id == media_id))
        ai_result = await session.scalar(
            select(MediaAiResult).where(MediaAiResult.media_item_id == media_id)
        )

    assert media_item is not None
    assert media_item.status == MediaStatus.COMPLETED
    assert media_item.thumbnail_s3_key is not None

    assert ai_result is not None
    assert ai_result.status == AiAnalysisStatus.COMPLETED
    assert ai_result.caption
    assert "mock" in ai_result.tags

    from common.enums import NotificationStatus
    from common.models import ProcessingNotification
    from sqlalchemy import select

    async with async_session_factory() as session:
        notification = await session.scalar(
            select(ProcessingNotification).where(ProcessingNotification.media_item_id == media_id)
        )

    assert notification is not None
    assert notification.status == NotificationStatus.SENT
    assert notification.event_status == "COMPLETED"
    assert notification.message == "Your image is ready"


@pytest.fixture(scope="session", autouse=True)
async def dispose_engine():
    yield
    await engine.dispose()
