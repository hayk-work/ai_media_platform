import uuid
from unittest.mock import patch

import pytest
from app.main import app
from common.db import get_db_session
from common.enums import MediaStatus
from httpx import ASGITransport, AsyncClient


class _FakeScalars:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class _FakeResult:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        self.committed = True

    async def refresh(self, _obj):
        return None

    async def execute(self, _statement):
        return _FakeResult(None)


@pytest.mark.asyncio
async def test_create_upload_returns_presigned_url_when_bucket_configured() -> None:
    user_id = uuid.uuid4()
    fake_user = type("User", (), {"id": user_id})()
    fake_session = _FakeSession()

    async def override_get_db():
        yield fake_session

    from app.dependencies import get_current_user

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with patch("app.routers.uploads.settings.s3_media_bucket", "test-bucket"), patch(
        "app.routers.uploads.generate_presigned_upload_url",
        return_value="https://example.com/presigned",
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/uploads",
                json={
                    "filename": "photo.jpg",
                    "content_type": "image/jpeg",
                    "file_size_bytes": 1024,
                },
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == MediaStatus.UPLOADING.value
    assert payload["upload_url"] == "https://example.com/presigned"
    media_items = [obj for obj in fake_session.added if hasattr(obj, "s3_key")]
    assert media_items[0].s3_key.startswith(f"uploads/{user_id}/")
