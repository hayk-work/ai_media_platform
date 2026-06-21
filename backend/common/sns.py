import json
import uuid
from typing import Any

import boto3
import structlog

from common.config import settings

logger = structlog.get_logger(__name__)


def _sns_client():
    return boto3.client("sns", region_name=settings.aws_region)


def build_processing_notification_payload(
    *,
    media_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    message: str,
) -> dict[str, str]:
    return {
        "media_id": str(media_id),
        "user_id": str(user_id),
        "status": status,
        "message": message,
    }


def publish_processing_notification(payload: dict[str, Any]) -> str:
    """Publish a processing notification to SNS.

    Returns the SNS MessageId when published, or ``local`` when running without a topic.
    Raises on publish failures when SNS is configured.
    """
    body = json.dumps(payload)
    if not settings.sns_enabled:
        logger.info(
            "sns_publish_skipped",
            reason="sns_topic_not_configured",
            payload=payload,
        )
        return "local"

    topic_arn = settings.sns_processing_topic_arn
    logger.info(
        "sns_publish_attempt",
        topic_arn=topic_arn,
        media_id=payload.get("media_id"),
        user_id=payload.get("user_id"),
        status=payload.get("status"),
    )
    try:
        response = _sns_client().publish(
            TopicArn=topic_arn,
            Message=body,
            Subject=f"Media processing {payload.get('status', 'update')}",
        )
    except Exception as exc:
        logger.exception(
            "sns_publish_failed",
            topic_arn=topic_arn,
            media_id=payload.get("media_id"),
            error=str(exc),
        )
        raise

    message_id = response["MessageId"]
    logger.info(
        "sns_notification_published",
        topic_arn=topic_arn,
        message_id=message_id,
        media_id=payload.get("media_id"),
        user_id=payload.get("user_id"),
        status=payload.get("status"),
    )
    return message_id
