import uuid
from datetime import datetime

from common.enums import AiAnalysisStatus, MediaStatus
from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    db: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class LogoutResponse(BaseModel):
    message: str


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0)


class UploadResponse(BaseModel):
    media_id: uuid.UUID
    upload_url: str | None = None
    status: MediaStatus


class ProcessingJobResponse(BaseModel):
    id: uuid.UUID
    status: MediaStatus
    attempt_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MediaAiResultResponse(BaseModel):
    id: uuid.UUID
    caption: str | None
    tags: list[str]
    labels: list[str]
    quality_issues: list[str]
    is_safe: bool
    provider: str | None
    model: str | None
    status: AiAnalysisStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MediaItemResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: MediaStatus
    s3_key: str | None
    thumbnail_s3_key: str | None
    thumbnail_url: str | None = None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime
    latest_job: ProcessingJobResponse | None = None
    ai_result: MediaAiResultResponse | None = None


class MediaListResponse(BaseModel):
    items: list[MediaItemResponse]


class NotificationPreferencesResponse(BaseModel):
    email_enabled: bool
    sms_enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: bool
    sms_enabled: bool = False
