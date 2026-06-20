import uuid

import boto3
from botocore.config import Config

from common.config import settings


def build_media_object_key(user_id: uuid.UUID, media_id: uuid.UUID, filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{user_id}/{media_id}/{safe_filename}"


def generate_presigned_upload_url(
    *,
    bucket: str,
    object_key: str,
    content_type: str,
    expires_in: int | None = None,
) -> str:
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in or settings.s3_presign_expires_seconds,
    )
