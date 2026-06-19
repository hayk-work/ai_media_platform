import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_returns_201(
    integration_client: AsyncClient, api_available, unique_email: str, auth_password: str
) -> None:
    response = await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == unique_email
    assert "id" in payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate_returns_409(
    integration_client: AsyncClient, api_available, unique_email: str, auth_password: str
) -> None:
    first = await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    assert first.status_code == 201

    second = await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    assert second.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_valid_returns_jwt(
    integration_client: AsyncClient, api_available, unique_email: str, auth_password: str
) -> None:
    register_response = await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    login_response = await integration_client.post(
        "/auth/login",
        json={"email": unique_email, "password": auth_password},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user_id"] == user_id
    assert isinstance(payload["access_token"], str)
    assert payload["access_token"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_returns_401(
    integration_client: AsyncClient, api_available, unique_email: str
) -> None:
    response = await integration_client.post(
        "/auth/login",
        json={"email": unique_email, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_requires_auth(integration_client: AsyncClient, api_available) -> None:
    response = await integration_client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_returns_current_user(
    integration_client: AsyncClient, api_available, unique_email: str, auth_password: str
) -> None:
    await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    login_response = await integration_client.post(
        "/auth/login",
        json={"email": unique_email, "password": auth_password},
    )
    token = login_response.json()["access_token"]

    me_response = await integration_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == unique_email


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_revokes_token(
    integration_client: AsyncClient, api_available, unique_email: str, auth_password: str
) -> None:
    await integration_client.post(
        "/auth/register",
        json={"email": unique_email, "password": auth_password},
    )
    login_response = await integration_client.post(
        "/auth/login",
        json={"email": unique_email, "password": auth_password},
    )
    token = login_response.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    logout_response = await integration_client.post("/auth/logout", headers=auth_header)
    assert logout_response.status_code == 200

    me_response = await integration_client.get("/auth/me", headers=auth_header)
    assert me_response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_protected_upload_rejects_invalid_token(
    integration_client: AsyncClient, api_available
) -> None:
    response = await integration_client.post(
        "/uploads",
        headers={"Authorization": "Bearer invalid-token"},
        json={
            "filename": "test.jpg",
            "content_type": "image/jpeg",
            "file_size_bytes": 100,
        },
    )
    assert response.status_code == 401
