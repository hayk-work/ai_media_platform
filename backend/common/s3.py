import uuid

import boto3
from botocore.config import Config

from common.config import settings


def build_media_object_key(user_id: uuid.UUID, media_id: uuid.UUID, filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{user_id}/{media_id}/{safe_filename}"


def build_thumbnail_object_key(user_id: uuid.UUID, media_id: uuid.UUID, filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    stem = safe_filename.rsplit(".", 1)[0]
    return f"thumbnails/{user_id}/{media_id}/{stem}.jpg"


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )


def download_object_bytes(*, bucket: str, object_key: str) -> bytes:
    client = _s3_client()
    response = client.get_object(Bucket=bucket, Key=object_key)
    return response["Body"].read()


def upload_object_bytes(
    *,
    bucket: str,
    object_key: str,
    body: bytes,
    content_type: str,
) -> None:
    client = _s3_client()
    client.put_object(Bucket=bucket, Key=object_key, Body=body, ContentType=content_type)


def generate_presigned_upload_url(
    *,
    bucket: str,
    object_key: str,
    content_type: str,
    expires_in: int | None = None,
) -> str:
    client = _s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in or settings.s3_presign_expires_seconds,
    )
