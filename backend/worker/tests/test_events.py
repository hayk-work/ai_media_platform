import json
import uuid

from common.sqs_events import extract_s3_object_from_message, normalize_event_payload


def test_extract_s3_object_from_eventbridge_message() -> None:
    body = json.dumps(
        {
            "detail-type": "Object Created",
            "source": "aws.s3",
            "detail": {
                "bucket": {"name": "media-bucket"},
                "object": {"key": "uploads/user/media/photo.jpg"},
            },
        }
    )
    assert extract_s3_object_from_message(body) == (
        "media-bucket",
        "uploads/user/media/photo.jpg",
    )


def test_extract_s3_object_from_s3_notification_message() -> None:
    body = json.dumps(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "media-bucket"},
                        "object": {"key": "uploads/user/media/photo.jpg"},
                    }
                }
            ]
        }
    )
    assert extract_s3_object_from_message(body) == (
        "media-bucket",
        "uploads/user/media/photo.jpg",
    )


def test_normalize_event_payload() -> None:
    payload = {
        "detail": {
            "bucket": {"name": "media-bucket"},
            "object": {"key": f"uploads/{uuid.uuid4()}/{uuid.uuid4()}/file.jpg"},
        }
    }
    assert normalize_event_payload(payload) is not None
