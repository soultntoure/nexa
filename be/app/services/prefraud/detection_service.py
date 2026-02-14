"""
Detection service — orchestrates pattern detection with Jaccard deduplication.

Contains:
- PatternDetectionService class (takes async_sessionmaker)
  - run_detection(trigger) -> DetectionRunResult

Responsibilities:
1. Runs all 5 detectors in parallel via asyncio.gather(return_exceptions=True)
2. Groups results by (pattern_type, group_key)
3. For each group: Jaccard dedup against existing patterns of same type
   - >= 0.8: skip (duplicate), update last_matched_at
   - 0.3-0.8: update existing pattern's matches (evolved)
   - < 0.3: create new CANDIDATE fraud_pattern + pattern_matches
4. Returns DetectionRunResult summary

Follows posture_service.py patterns: session_factory in __init__,
each operation opens its own session.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.data.db.models.fraud_pattern import FraudPattern
from app.data.db.models.pattern_match import PatternMatch
from app.data.db.repositories.pattern_match_repository import PatternMatchRepository
from app.data.db.repositories.pattern_repository import PatternRepository
from app.services.prefraud.detectors import ALL_DETECTORS
from app.services.prefraud.detectors.base import PatternDetector, PatternMatchResult

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DetectionRunResult:
    trigger: str
    new_candidates: int
    updated_patterns: int
    skipped_duplicates: int
    total_matches: int
    elapsed_s: float


def compute_jaccard(new_customer_ids: set[UUID], existing_customer_ids: set[UUID]) -> float:
    """Jaccard similarity between two customer ID sets."""
    intersection = len(new_customer_ids & existing_customer_ids)
    union = len(new_customer_ids | existing_customer_ids)
    return intersection / union if union > 0 else 0.0


class PatternDetectionService:
    """Orchestrates detection across all pattern types with deduplication."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def run_detection(self, trigger: str = "scheduled") -> DetectionRunResult:
        """Run all detectors, deduplicate, and persist results.

        Error isolation: asyncio.gather(return_exceptions=True) ensures one
        failing detector does not cancel the other four.
        """
        start = time.monotonic()

        # Step 1: Run all detectors in parallel
        detectors = [cls() for cls in ALL_DETECTORS]
        tasks = [self._run_detector(d) for d in detectors]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results, log failures
        all_matches: list[tuple[str, PatternMatchResult]] = []
        for detector, result in zip(detectors, raw_results):
            if isinstance(result, BaseException):
                logger.error(
                    "Detector %s failed: %s", detector.pattern_type, result,
                )
                continue
            for match in result:
                all_matches.append((detector.pattern_type, match))

        logger.info(
            "Detection run: %d total matches from %d detectors (trigger=%s)",
            len(all_matches), len(detectors), trigger,
        )

        # Step 2: Group by (pattern_type, group_key)
        groups: dict[tuple[str, str | None], list[PatternMatchResult]] = defaultdict(list)
        for pattern_type, match in all_matches:
            groups[(pattern_type, match.group_key)].append(match)

        # Step 3: Deduplicate and persist
        new_candidates = 0
        updated_patterns = 0
        skipped_duplicates = 0
        total_matches = 0

        for (pattern_type, group_key), matches in groups.items():
            try:
                action = await self._process_group(
                    pattern_type, group_key, matches,
                )
                if action == "created":
                    new_candidates += 1
                    total_matches += len(matches)
                elif action == "updated":
                    updated_patterns += 1
                    total_matches += len(matches)
                elif action == "skipped":
                    skipped_duplicates += 1
            except Exception:
                logger.exception(
                    "Failed to process group pattern_type=%s group_key=%s",
                    pattern_type, group_key,
                )

        elapsed = round(time.monotonic() - start, 3)

        logger.info(
            "Detection complete: new=%d updated=%d skipped=%d matches=%d elapsed=%.3fs",
            new_candidates, updated_patterns, skipped_duplicates,
            total_matches, elapsed,
        )

        return DetectionRunResult(
            trigger=trigger,
            new_candidates=new_candidates,
            updated_patterns=updated_patterns,
            skipped_duplicates=skipped_duplicates,
            total_matches=total_matches,
            elapsed_s=elapsed,
        )

    async def _run_detector(self, detector: PatternDetector) -> list[PatternMatchResult]:
        """Run a single detector with its own session."""
        async with self._session_factory() as session:
            return await detector.detect(session)

    async def _process_group(
        self,
        pattern_type: str,
        group_key: str | None,
        matches: list[PatternMatchResult],
    ) -> str:
        """Deduplicate a result group against existing patterns and persist.

        Returns:
            "created", "updated", or "skipped"
        """
        new_customer_ids = {m.customer_id for m in matches}

        # Find best Jaccard overlap against existing patterns
        best_jaccard = 0.0
        best_pattern_id: UUID | None = None

        async with self._session_factory() as session:
            pattern_repo = PatternRepository(session)
            match_repo = PatternMatchRepository(session)

            existing_patterns = await pattern_repo.get_by_type_and_state(
                pattern_type, ["active", "candidate"],
            )

            for ep in existing_patterns:
                ep_matches = await match_repo.get_by_pattern(ep.id)
                existing_ids = {m.customer_id for m in ep_matches}
                jaccard = compute_jaccard(new_customer_ids, existing_ids)
                if jaccard > best_jaccard:
                    best_jaccard = jaccard
                    best_pattern_id = ep.id

        # Decision based on Jaccard threshold
        if best_jaccard >= 0.8 and best_pattern_id is not None:
            return await self._handle_duplicate(best_pattern_id)
        elif best_jaccard >= 0.3 and best_pattern_id is not None:
            return await self._handle_evolved(best_pattern_id, matches)
        else:
            return await self._handle_new_candidate(
                pattern_type, group_key, matches,
            )

    async def _handle_duplicate(self, pattern_id: UUID) -> str:
        """Skip duplicate but update last_matched_at."""
        async with self._session_factory() as session:
            repo = PatternRepository(session)
            await repo.update_last_matched(pattern_id)
        return "skipped"

    async def _handle_evolved(
        self,
        pattern_id: UUID,
        matches: list[PatternMatchResult],
    ) -> str:
        """Update existing pattern's matches for evolved overlap (0.3-0.8)."""
        async with self._session_factory() as session:
            pattern_repo = PatternRepository(session)
            match_repo = PatternMatchRepository(session)

            new_match_rows = [
                PatternMatch(
                    pattern_id=pattern_id,
                    customer_id=m.customer_id,
                    confidence=m.confidence,
                    evidence=m.evidence,
                )
                for m in matches
            ]
            await match_repo.bulk_upsert(pattern_id, new_match_rows)
            await pattern_repo.update_last_matched(pattern_id)
            await pattern_repo.increment_frequency(pattern_id)

        return "updated"

    async def _handle_new_candidate(
        self,
        pattern_type: str,
        group_key: str | None,
        matches: list[PatternMatchResult],
    ) -> str:
        """Create a new CANDIDATE fraud_pattern with its pattern_matches."""
        avg_confidence = sum(m.confidence for m in matches) / len(matches)
        now = _utcnow()

        new_pattern = FraudPattern(
            pattern_type=pattern_type,
            description=(
                f"Auto-detected {pattern_type} pattern "
                f"({len(matches)} customers)"
            ),
            definition={
                "group_key": group_key,
                "customer_count": len(matches),
            },
            evidence=_aggregate_evidence(matches),
            state="candidate",
            confidence=round(avg_confidence, 4),
            frequency=1,
            detected_at=now,
            last_matched_at=now,
        )

        async with self._session_factory() as session:
            pattern_repo = PatternRepository(session)
            match_repo = PatternMatchRepository(session)

            saved_pattern = await pattern_repo.create(new_pattern)

            match_rows = [
                PatternMatch(
                    pattern_id=saved_pattern.id,
                    customer_id=m.customer_id,
                    confidence=m.confidence,
                    evidence=m.evidence,
                )
                for m in matches
            ]
            await match_repo.bulk_upsert(saved_pattern.id, match_rows)

        return "created"


def _aggregate_evidence(matches: list[PatternMatchResult]) -> dict:
    """Combine per-match evidence into a pattern-level summary."""
    customer_ids = [str(m.customer_id) for m in matches]
    confidences = [m.confidence for m in matches]

    return {
        "customer_count": len(matches),
        "customer_ids": customer_ids,
        "avg_confidence": round(sum(confidences) / len(confidences), 4),
        "min_confidence": round(min(confidences), 4),
        "max_confidence": round(max(confidences), 4),
    }
