"""
Detection scheduler — background async loop for periodic pattern detection.

Contains:
- start_detection_scheduler(detection_service) -> asyncio.Task
  Launches a background loop that runs pattern detection at a configurable
  interval (PATTERN_DETECTION_INTERVAL_S, default 43200s / 12 hours).

- trigger_detection(detection_service, trigger)
  Fire-and-forget helper for event-driven detection runs.
  Used when a withdrawal is confirmed as fraud.

The scheduler is registered in FastAPI lifespan and cancelled on shutdown.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.services.prefraud.detection_service import PatternDetectionService

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_S = 43200  # 12 hours


async def _detection_scheduler_loop(service: PatternDetectionService) -> None:
    """Run detection at a fixed interval until cancelled."""
    settings = get_settings()
    interval = getattr(settings, "PATTERN_DETECTION_INTERVAL_S", _DEFAULT_INTERVAL_S)

    logger.info("Detection scheduler started (interval=%ds)", interval)

    while True:
        await asyncio.sleep(interval)
        try:
            result = await service.run_detection(trigger="scheduled")
            logger.info(
                "Scheduled detection completed: new=%d updated=%d skipped=%d",
                result.new_candidates, result.updated_patterns,
                result.skipped_duplicates,
            )
        except Exception:
            logger.exception("Scheduled pattern detection failed")


def start_detection_scheduler(service: PatternDetectionService) -> asyncio.Task:
    """Launch the background scheduler loop as an asyncio task.

    Returns the task so it can be cancelled on shutdown.
    """
    return asyncio.create_task(_detection_scheduler_loop(service))


def trigger_detection(service: PatternDetectionService, trigger: str) -> None:
    """Fire-and-forget pattern detection run.

    Creates an asyncio task that runs independently. The calling
    operation does NOT await the detection — results are persisted
    to the database for later consumption.

    Args:
        service: PatternDetectionService instance (typically from app.state)
        trigger: Trigger source (e.g. 'event:fraud_confirmed')
    """
    asyncio.create_task(_safe_detection(service, trigger))


async def _safe_detection(service: PatternDetectionService, trigger: str) -> None:
    """Run detection with error handling so the task never crashes silently."""
    try:
        await service.run_detection(trigger=trigger)
    except Exception:
        logger.exception(
            "Event-driven pattern detection failed: trigger=%s", trigger,
        )
