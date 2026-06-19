import os

import httpx
import pytest

INTEGRATION_BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000")


@pytest.fixture
async def integration_client():
    async with httpx.AsyncClient(base_url=INTEGRATION_BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture
async def api_available(integration_client: httpx.AsyncClient):
    try:
        response = await integration_client.get("/health")
        if response.status_code != 200:
            pytest.skip(f"API not healthy at {INTEGRATION_BASE_URL}")
    except httpx.HTTPError as exc:
        pytest.skip(f"API not reachable at {INTEGRATION_BASE_URL}: {exc}")
