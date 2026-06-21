import asyncio
from typing import Any

import boto3
import structlog
from common.config import settings
from common.db import async_session_factory
from common.media_processing import process_upload_object
from common.sqs_events import extract_s3_object_from_message

logger = structlog.get_logger(__name__)


def _sqs_client():
    return boto3.client("sqs", region_name=settings.aws_region)


def receive_messages() -> list[dict[str, Any]]:
    if not settings.sqs_processing_queue_url:
        return []

    response = _sqs_client().receive_message(
        QueueUrl=settings.sqs_processing_queue_url,
        MaxNumberOfMessages=settings.worker_max_messages,
        WaitTimeSeconds=settings.worker_poll_wait_seconds,
        MessageAttributeNames=["All"],
    )
    return response.get("Messages", [])


def delete_message(receipt_handle: str) -> None:
    _sqs_client().delete_message(
        QueueUrl=settings.sqs_processing_queue_url,
        ReceiptHandle=receipt_handle,
    )


async def handle_message(message: dict[str, Any]) -> bool:
    body = message.get("Body", "")
    parsed = extract_s3_object_from_message(body)
    if parsed is None:
        logger.warning("sqs_message_unparseable", body=body)
        return True

    bucket, object_key = parsed
    logger.info(
        "sqs_message_received",
        message_id=message.get("MessageId"),
        bucket=bucket,
        object_key=object_key,
    )
    bucket_name = settings.s3_media_bucket or bucket
    return await process_upload_object(
        async_session_factory,
        bucket=bucket_name,
        object_key=object_key,
    )


async def poll_and_process_once() -> int:
    messages = await asyncio.to_thread(receive_messages)
    processed = 0
    for message in messages:
        receipt_handle = message["ReceiptHandle"]
        try:
            should_delete = await handle_message(message)
            if should_delete:
                await asyncio.to_thread(delete_message, receipt_handle)
                processed += 1
        except Exception:
            logger.exception("sqs_message_failed", message_id=message.get("MessageId"))
    return processed
