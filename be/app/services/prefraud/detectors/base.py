"""Detector framework — protocol and result dataclass for pattern detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PatternMatchResult:
    """Single match returned by a detector."""

    customer_id: UUID
    confidence: float  # 0-1
    evidence: dict  # What specifically matched
    group_key: str | None  # For ring patterns: identifier grouping related matches


class PatternDetector(Protocol):
    """Common protocol all detectors implement."""

    pattern_type: str

    async def detect(self, session: AsyncSession) -> list[PatternMatchResult]:
        """Run detection query and return matches."""
        ...
