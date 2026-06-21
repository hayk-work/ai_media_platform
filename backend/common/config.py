from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://amp:amp@localhost:5432/ai_media_platform"
    db_host: str = ""
    db_port: int = 5432
    db_user: str = "amp"
    db_password: str = ""
    db_name: str = "ai_media_platform"
    jwt_secret: str = "local-dev-jwt-secret-change-in-production-32b"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    aws_region: str = "us-east-1"
    s3_media_bucket: str = ""
    s3_presign_expires_seconds: int = 900
    sqs_processing_queue_url: str = ""
    worker_poll_wait_seconds: int = 20
    worker_max_messages: int = 1
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    ai_mock_mode: bool = False

    @property
    def ai_enabled(self) -> bool:
        return self.ai_mock_mode or bool(self.groq_api_key)

    @property
    def resolved_database_url(self) -> str:
        if self.db_host:
            return (
                f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self.database_url


settings = Settings()
