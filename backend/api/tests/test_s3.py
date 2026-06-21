import uuid

import boto3
import pytest
from common.config import Settings
from common.s3 import build_media_object_key, generate_presigned_upload_url
from moto import mock_aws


def test_build_media_object_key_sanitizes_filename() -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    key = build_media_object_key(user_id, media_id, "vacation/photo.jpg")
    assert key == f"uploads/{user_id}/{media_id}/vacation_photo.jpg"


@mock_aws
def test_generate_presigned_upload_url_includes_bucket_and_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bucket = "test-media-bucket"
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=bucket)

    settings = Settings(
        aws_region="us-east-1",
        s3_media_bucket=bucket,
        s3_presign_expires_seconds=900,
    )
    monkeypatch.setattr("common.s3.settings", settings)
    object_key = "uploads/user/media/photo.jpg"

    url = generate_presigned_upload_url(
        bucket=bucket,
        object_key=object_key,
        content_type="image/jpeg",
    )

    assert bucket in url
    assert "photo.jpg" in url
    assert url.startswith("https://")
