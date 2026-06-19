import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(mocked_db_client: AsyncClient) -> None:
    response = await mocked_db_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["db"] == "connected"


async def _register_and_login(
    client: AsyncClient, email: str, password: str
) -> tuple[str, dict[str, str]]:
    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_login_upload_list_and_get_flow(
    integration_client: AsyncClient, api_available
) -> None:
    email = f"integration-{uuid.uuid4()}@example.com"
    password = "integration-password-123"
    _, auth_header = await _register_and_login(integration_client, email, password)

    me_response = await integration_client.get("/auth/me", headers=auth_header)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

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

    get_response = await integration_client.get(f"/media/{media_id}", headers=auth_header)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == media_id


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
