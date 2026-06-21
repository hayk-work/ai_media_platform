import os

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-with-32-bytes-minimum")
os.environ.setdefault("AI_MOCK_MODE", "true")
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://amp:amp@localhost:5433/ai_media_platform",
)

import uuid

import httpx
import pytest
from app.main import app
from common.db import engine, get_db_session
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

INTEGRATION_BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000")


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


@pytest.fixture
async def integration_client():
    async with httpx.AsyncClient(base_url=INTEGRATION_BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture
async def db_available():
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")


@pytest.fixture
async def api_available(integration_client: httpx.AsyncClient):
    try:
        response = await integration_client.get("/health")
        if response.status_code != 200:
            pytest.skip(f"API not healthy at {INTEGRATION_BASE_URL}")
    except httpx.HTTPError as exc:
        pytest.skip(f"API not reachable at {INTEGRATION_BASE_URL}: {exc}")


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4()}@example.com"


@pytest.fixture
def auth_password() -> str:
    return "strong-password-123"
