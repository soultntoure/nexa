"""
Posture scheduler — background async loop for periodic recomputation.

Contains:
- start_posture_scheduler(posture_service) -> asyncio.Task
  Launches a background loop that recomputes posture for all customers
  at a configurable interval (POSTURE_RECOMPUTE_INTERVAL_S, default 3600s).

- trigger_recompute(posture_service, customer_id, trigger)
  Fire-and-forget helper for event-driven recomputation.
  Used at trigger points: new device, new method, new IP, withdrawal, failed tx.

The scheduler is registered in FastAPI lifespan and cancelled on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.config import get_settings
from app.services.prefraud.posture_service import PostureService

logger = logging.getLogger(__name__)


async def _scheduler_loop(service: PostureService) -> None:
    """Run recompute_all() at a fixed interval until cancelled."""
    settings = get_settings()
    interval = settings.POSTURE_RECOMPUTE_INTERVAL_S

    logger.info("Posture scheduler started (interval=%ds)", interval)

    while True:
        await asyncio.sleep(interval)
        try:
            snapshots = await service.recompute_all(trigger="scheduled")
            logger.info(
                "Scheduled recompute completed: %d customers",
                len(snapshots),
            )
        except Exception:
            logger.exception("Scheduled posture recompute failed")


def start_posture_scheduler(service: PostureService) -> asyncio.Task:
    """Launch the background scheduler loop as an asyncio task.

    Returns the task so it can be cancelled on shutdown.
    """
    return asyncio.create_task(_scheduler_loop(service))


def trigger_recompute(
    service: PostureService,
    customer_id: uuid.UUID,
    trigger: str,
) -> None:
    """Fire-and-forget posture recompute for a single customer.

    Creates an asyncio task that runs independently. The calling
    operation does NOT await the recompute — the investigation
    pipeline reads the last completed posture snapshot.

    Args:
        service: PostureService instance (typically from app.state)
        customer_id: UUID of the customer to recompute
        trigger: Trigger source (e.g. 'event:withdrawal_request')
    """
    asyncio.create_task(
        _safe_recompute(service, customer_id, trigger),
    )


async def _safe_recompute(
    service: PostureService,
    customer_id: uuid.UUID,
    trigger: str,
) -> None:
    """Run recompute with error handling so the task never crashes silently."""
    try:
        await service.recompute(customer_id, trigger=trigger)
    except Exception:
        logger.exception(
            "Event-driven posture recompute failed: customer=%s trigger=%s",
            customer_id, trigger,
        )
