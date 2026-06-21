import uuid

import pytest
from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
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
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_notification_preferences_require_auth(
    integration_client: AsyncClient, api_available
) -> None:
    response = await integration_client.get("/notifications/preferences")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_notification_preferences_default_and_update(
    integration_client: AsyncClient, api_available
) -> None:
    email = f"notifications-{uuid.uuid4()}@example.com"
    password = "strong-password-123"
    auth_header = await _register_and_login(integration_client, email, password)

    get_response = await integration_client.get(
        "/notifications/preferences",
        headers=auth_header,
    )
    assert get_response.status_code == 200
    assert get_response.json() == {"email_enabled": True, "sms_enabled": False}

    update_response = await integration_client.put(
        "/notifications/preferences",
        headers=auth_header,
        json={"email_enabled": False, "sms_enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json() == {"email_enabled": False, "sms_enabled": False}

    get_response = await integration_client.get(
        "/notifications/preferences",
        headers=auth_header,
    )
    assert get_response.status_code == 200
    assert get_response.json() == {"email_enabled": False, "sms_enabled": False}
