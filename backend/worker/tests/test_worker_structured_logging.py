import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from structlog.testing import capture_logs
from worker.app.processor import handle_message


@pytest.mark.asyncio
async def test_handle_message_logs_sqs_message_received() -> None:
    media_id = uuid.uuid4()
    user_id = uuid.uuid4()
    object_key = f"uploads/{user_id}/{media_id}/photo.jpg"
    message = {
        "MessageId": "msg-123",
        "Body": json.dumps(
            {
                "detail": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": object_key},
                }
            }
        ),
    }

    with capture_logs() as captured_logs, patch(
        "worker.app.processor.process_upload_object",
        new=AsyncMock(return_value=True),
    ):
        handled = await handle_message(message)

    assert handled is True
    received = next(
        entry for entry in captured_logs if entry.get("event") == "sqs_message_received"
    )
    assert received["message_id"] == "msg-123"
    assert received["object_key"] == object_key
