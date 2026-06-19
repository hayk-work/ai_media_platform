import asyncio
import signal

import structlog
from common.config import settings
from common.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)

_shutdown = False


def _handle_shutdown(signum: int, _frame: object) -> None:
    global _shutdown
    logger.info("shutdown_signal_received", signal=signum)
    _shutdown = True


async def process_message(payload: dict) -> None:
    """Placeholder for future SQS message handling."""
    logger.info("process_message_placeholder", payload=payload)


async def run_worker() -> None:
    logger.info(
        "worker_started",
        environment=settings.environment,
        message="Waiting for SQS messages (not connected in Sprint 01).",
    )

    while not _shutdown:
        logger.info("worker_idle", status="polling_placeholder")
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            break

    logger.info("worker_stopped")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
