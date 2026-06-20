from common.config import Settings


def test_resolved_database_url_uses_components_when_db_host_set() -> None:
    settings = Settings(
        db_host="db.example.com",
        db_user="amp",
        db_password="secret",
        db_name="ai_media_platform",
        db_port=5432,
    )
    assert (
        settings.resolved_database_url
        == "postgresql+asyncpg://amp:secret@db.example.com:5432/ai_media_platform"
    )


def test_resolved_database_url_falls_back_to_database_url() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://amp:amp@localhost:5433/ai_media_platform",
    )
    assert settings.resolved_database_url == settings.database_url
