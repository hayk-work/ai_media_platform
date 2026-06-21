import uuid
from unittest.mock import patch

import pytest
import structlog
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

from app.dependencies import get_current_user
from app.main import app
from common.db import get_db_session


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_upload_request_emits_structured_logs() -> None:
    user_id = uuid.uuid4()
    fake_user = type("User", (), {"id": user_id})()
    fake_session = _FakeSession()

    async def override_get_db():
        yield fake_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with capture_logs() as captured_logs, patch(
        "app.routers.uploads.settings.s3_media_bucket", "test-bucket"
    ), patch(
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
    event_names = {entry.get("event") for entry in captured_logs}
    assert "upload_requested" in event_names
    assert "presigned_url_generated" in event_names

    upload_requested = next(entry for entry in captured_logs if entry.get("event") == "upload_requested")
    assert upload_requested["filename"] == "photo.jpg"
    assert upload_requested["content_type"] == "image/jpeg"

    presigned = next(
        entry for entry in captured_logs if entry.get("event") == "presigned_url_generated"
    )
    assert presigned["bucket"] == "test-bucket"
    assert presigned["s3_key"].startswith("uploads/")


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    from common.logging import configure_logging

    configure_logging()
    logger = structlog.get_logger("test")
    logger.info("health_probe", status="ok")

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["event"] == "health_probe"
    assert payload["status"] == "ok"
    assert payload["level"] == "info"
