import os

os.environ.setdefault("AI_MOCK_MODE", "true")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://amp:amp@localhost:5433/ai_media_platform",
    ),
)

import pytest
from common.db import engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker


@pytest.fixture
async def db_available():
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available: {exc}")


@pytest.fixture(scope="session", autouse=True)
async def dispose_engine():
    yield
    await engine.dispose()
