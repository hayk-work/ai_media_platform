import uuid
from io import BytesIO

import pytest
from moto import mock_aws
from PIL import Image

from common.media_processing import (
    create_thumbnail_image,
    parse_upload_object_key,
)
from common.s3 import build_thumbnail_object_key, download_object_bytes, upload_object_bytes


def test_parse_upload_object_key() -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    key = f"uploads/{user_id}/{media_id}/photo.jpg"
    ref = parse_upload_object_key(key)
    assert ref is not None
    assert ref.user_id == user_id
    assert ref.media_id == media_id
    assert ref.filename == "photo.jpg"


def test_parse_upload_object_key_rejects_invalid_prefix() -> None:
    assert parse_upload_object_key("thumbnails/a/b/c.jpg") is None


def test_create_thumbnail_image() -> None:
    image = Image.new("RGB", (640, 480), color="red")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    thumbnail_bytes, metadata = create_thumbnail_image(buffer.getvalue())
    assert thumbnail_bytes
    assert metadata["original_width"] == 640
    assert metadata["original_height"] == 480
    assert metadata["thumbnail_width"] <= 256
    assert metadata["thumbnail_height"] <= 256


def test_build_thumbnail_object_key_uses_jpg_suffix() -> None:
    user_id = uuid.uuid4()
    media_id = uuid.uuid4()
    key = build_thumbnail_object_key(user_id, media_id, "photo.png")
    assert key.endswith("/photo.jpg")


@mock_aws
def test_s3_round_trip_for_processing() -> None:
    import boto3

    bucket = "processing-test-bucket"
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=bucket)
    object_key = "uploads/u/m/original.jpg"
    upload_object_bytes(
        bucket=bucket,
        object_key=object_key,
        body=b"original-bytes",
        content_type="image/jpeg",
    )
    assert download_object_bytes(bucket=bucket, object_key=object_key) == b"original-bytes"
