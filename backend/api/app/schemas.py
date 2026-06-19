import uuid
from datetime import datetime

from common.enums import MediaStatus
from pydantic import BaseModel, EmailStr, Field


class HealthResponse(BaseModel):
    status: str
    db: str


class SessionRequest(BaseModel):
    email: EmailStr


class SessionResponse(BaseModel):
    user_id: uuid.UUID
    token: str


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0)


class UploadResponse(BaseModel):
    media_id: uuid.UUID
    status: MediaStatus


class ProcessingJobResponse(BaseModel):
    id: uuid.UUID
    status: MediaStatus
    attempt_count: int
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
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime
    latest_job: ProcessingJobResponse | None = None


class MediaListResponse(BaseModel):
    items: list[MediaItemResponse]
