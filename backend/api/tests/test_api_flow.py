import uuid

import pytest
from app.main import app
from common.db import get_db_session
from httpx import ASGITransport, AsyncClient


class _FakeResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    async def execute(self, _statement):
        return _FakeResult()


@pytest.fixture
async def mocked_db_client():
    async def override_get_db():
        yield _FakeSession()  # type: ignore[misc]

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_returns_ok(mocked_db_client: AsyncClient) -> None:
    response = await mocked_db_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db"] == "connected"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_upload_list_and_get_flow(
    integration_client: AsyncClient, api_available
) -> None:
    email = f"integration-{uuid.uuid4()}@example.com"

    session_response = await integration_client.post("/auth/session", json={"email": email})
    assert session_response.status_code == 200
    session_payload = session_response.json()
    user_id = session_payload["user_id"]
    token = session_payload["token"]
    assert token == user_id
    auth_header = {"Authorization": f"Bearer {token}"}

    upload_response = await integration_client.post(
        "/uploads",
        headers=auth_header,
        json={
            "filename": "integration-test.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 2048,
        },
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    media_id = upload_payload["media_id"]
    assert upload_payload["status"] == "UPLOADING"

    list_response = await integration_client.get("/media", headers=auth_header)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["items"]) >= 1
    listed = next(item for item in list_payload["items"] if item["id"] == media_id)
    assert listed["filename"] == "integration-test.jpg"
    assert listed["content_type"] == "image/jpeg"
    assert listed["file_size_bytes"] == 2048
    assert listed["status"] == "UPLOADING"
    assert listed["latest_job"] is not None
    assert listed["latest_job"]["status"] == "UPLOADING"

    get_response = await integration_client.get(f"/media/{media_id}", headers=auth_header)
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["id"] == media_id
    assert get_payload["filename"] == "integration-test.jpg"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_requires_auth(integration_client: AsyncClient, api_available) -> None:
    response = await integration_client.post(
        "/uploads",
        json={
            "filename": "unauthorized.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 100,
        },
    )
    assert response.status_code == 401
