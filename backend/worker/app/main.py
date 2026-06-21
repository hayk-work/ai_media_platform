import asyncio
import signal

import structlog
from common.config import settings
from common.logging import configure_logging

from app.processor import poll_and_process_once

configure_logging()
logger = structlog.get_logger(__name__)

_shutdown = False


def _handle_shutdown(signum: int, _frame: object) -> None:
    global _shutdown
    logger.info("shutdown_signal_received", signal=signum)
    _shutdown = True


async def run_worker() -> None:
    logger.info(
        "worker_started",
        environment=settings.environment,
        queue_configured=bool(settings.sqs_processing_queue_url),
        bucket=settings.s3_media_bucket or None,
    )

    while not _shutdown:
        if not settings.sqs_processing_queue_url:
            logger.info("worker_idle", reason="sqs_processing_queue_url not configured")
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            continue

        processed = await poll_and_process_once()
        if processed == 0:
            logger.debug("worker_poll_empty")

    logger.info("worker_stopped")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
