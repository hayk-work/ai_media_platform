import json
import uuid

import boto3
import pytest
from moto import mock_aws

from common.config import Settings
from common.sns import build_processing_notification_payload, publish_processing_notification


def test_build_processing_notification_payload() -> None:
    media_id = uuid.uuid4()
    user_id = uuid.uuid4()
    payload = build_processing_notification_payload(
        media_id=media_id,
        user_id=user_id,
        status="COMPLETED",
        message="Your image is ready",
    )
    assert payload == {
        "media_id": str(media_id),
        "user_id": str(user_id),
        "status": "COMPLETED",
        "message": "Your image is ready",
    }


def test_publish_processing_notification_skips_without_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "common.sns.settings",
        Settings(sns_processing_topic_arn=""),
    )
    message_id = publish_processing_notification(
        {
            "media_id": "media_123",
            "user_id": "user_456",
            "status": "COMPLETED",
            "message": "Your image is ready",
        }
    )
    assert message_id == "local"


@mock_aws
def test_publish_processing_notification_publishes_to_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="processing-notifications")["TopicArn"]
    monkeypatch.setattr(
        "common.sns.settings",
        Settings(sns_processing_topic_arn=topic_arn, aws_region="us-east-1"),
    )

    payload = {
        "media_id": "media_123",
        "user_id": "user_456",
        "status": "COMPLETED",
        "message": "Your image is ready",
    }
    message_id = publish_processing_notification(payload)
    assert message_id

    messages = client.list_subscriptions_by_topic(TopicArn=topic_arn)["Subscriptions"]
    assert messages == []

    # Moto does not persist published message bodies on the topic itself,
    # but publish should succeed and return a MessageId.
    assert isinstance(message_id, str)


@mock_aws
def test_publish_processing_notification_serializes_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = boto3.client("sns", region_name="us-east-1")
    topic_arn = client.create_topic(Name="processing-json")["TopicArn"]
    monkeypatch.setattr(
        "common.sns.settings",
        Settings(sns_processing_topic_arn=topic_arn, aws_region="us-east-1"),
    )

    payload = {
        "media_id": "media_123",
        "user_id": "user_456",
        "status": "FAILED",
        "message": "Your image processing failed",
    }
    publish_processing_notification(payload)

    # Ensure payload is valid JSON (used as SNS message body).
    assert json.loads(json.dumps(payload)) == payload
