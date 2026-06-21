import uuid

import pytest
from app.main import app
from common.cdn import build_cloudfront_media_url
from common.config import settings
from common.db import async_session_factory
from common.enums import MediaStatus
from common.models import MediaItem, User
from common.security import hash_password
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_media_response_includes_cloudfront_thumbnail_url(
    db_available, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "cloudfront_media_base_url", "https://cdn.example.com")

    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    thumbnail_key = f"thumbnails/{user_id}/{media_id}/photo.jpg"

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"cdn-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="photo.jpg",
                content_type="image/jpeg",
                file_size_bytes=1024,
                status=MediaStatus.COMPLETED,
                thumbnail_s3_key=thumbnail_key,
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
        response = await client.get(f"/media/{media_id}", headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["thumbnail_s3_key"] == thumbnail_key
    assert payload["thumbnail_url"] == build_cloudfront_media_url(thumbnail_key)


@pytest.mark.asyncio
async def test_media_response_omits_thumbnail_url_without_cdn_config(
    db_available, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "cloudfront_media_base_url", "")

    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    thumbnail_key = f"thumbnails/{user_id}/{media_id}/photo.jpg"

    async with async_session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=f"cdn-off-{uuid.uuid4()}@example.com",
                password_hash=hash_password("strong-password-123"),
            )
        )
        session.add(
            MediaItem(
                id=media_id,
                user_id=user_id,
                filename="photo.jpg",
                content_type="image/jpeg",
                file_size_bytes=1024,
                status=MediaStatus.COMPLETED,
                thumbnail_s3_key=thumbnail_key,
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
        response = await client.get(f"/media/{media_id}", headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["thumbnail_url"] is None

