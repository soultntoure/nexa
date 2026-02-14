"""Cluster qualification and investigation helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from app.core.background_audit.pattern_analysis import meets_quality_gate
from app.services.background_audit.components.candidate_utils import (
    avg_confidence,
    build_pattern_card,
    novelty_to_float,
)
from app.services.background_audit.components.embed_cluster import ClusterData

EmitFn = Callable[[str, dict[str, Any]], Any]
InvestigationResult = tuple[ClusterData, dict[str, Any], float, int, int]

_INVESTIGATION_CONCURRENCY = 4


@dataclass(slots=True)
class QualifyingCluster:
    cluster: ClusterData
    events: int
    accounts: int
    confidence: float


class ClusterInvestigationService:
    """Phase 1-2: quality gate and parallel cluster investigation."""

    def __init__(
        self,
        agent: Any | None,
        emit: EmitFn | None,
        quality_gate_config: dict[str, Any],
        concurrency: int = _INVESTIGATION_CONCURRENCY,
    ) -> None:
        self._agent = agent
        self._emit = emit
        self._quality_gate_config = quality_gate_config
        self._concurrency = concurrency

    def select_qualifying(self, clusters: list[ClusterData]) -> list[QualifyingCluster]:
        qualifying: list[QualifyingCluster] = []
        for cluster in clusters:
            events, accounts, conf = self._cluster_stats(cluster)
            if meets_quality_gate(events, accounts, conf, **self._quality_gate_config):
                qualifying.append(
                    QualifyingCluster(
                        cluster=cluster,
                        events=events,
                        accounts=accounts,
                        confidence=conf,
                    )
                )
        return qualifying

    async def investigate(
        self,
        qualifying: list[QualifyingCluster],
    ) -> list[InvestigationResult | BaseException]:
        if not qualifying:
            return []

        sem = asyncio.Semaphore(self._concurrency)
        tasks = [
            self._investigate_single(qualifying_cluster, idx, len(qualifying), sem)
            for idx, qualifying_cluster in enumerate(qualifying)
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _investigate_single(
        self,
        qualifying_cluster: QualifyingCluster,
        idx: int,
        total_qualifying: int,
        sem: asyncio.Semaphore,
    ) -> InvestigationResult:
        cluster = qualifying_cluster.cluster
        events = qualifying_cluster.events
        accounts = qualifying_cluster.accounts
        conf = qualifying_cluster.confidence

        async with sem:
            if self._emit:
                narration = self._cluster_narration(cluster, events, accounts)
                source_types = sorted({u.source_name for u in cluster.units if u.source_name})
                await self._emit(
                    "hypothesis",
                    {
                        "title": self._cluster_label(cluster),
                        "phase": "investigate",
                        "detail": f"{events} events across {accounts} accounts",
                        "narration": narration,
                        "cluster_id": cluster.cluster_id,
                        "event_count": events,
                        "unit_count": events,
                        "account_count": accounts,
                        "source_types": source_types,
                        "novelty": novelty_to_float(cluster.novelty.status),
                        "progress": idx / max(total_qualifying, 1),
                    },
                )
            pattern_card, _ = await build_pattern_card(cluster, self._agent, self._emit)
            return cluster, pattern_card, conf, events, accounts

    @staticmethod
    def _cluster_stats(cluster: ClusterData) -> tuple[int, int, float]:
        events = len(cluster.units)
        accounts = len({str(u.withdrawal_id) for u in cluster.units})
        conf = avg_confidence(cluster.units)
        return events, accounts, conf

    @staticmethod
    def _cluster_label(cluster: ClusterData) -> str:
        sources = list({u.source_name for u in cluster.units})
        preview = cluster.units[0].text_masked[:80] if cluster.units else ""
        return f"{', '.join(sources[:2])}: {preview}..."

    @staticmethod
    def _cluster_narration(cluster: ClusterData, events: int, accounts: int) -> str:
        """Build a plain-English description of what the agent is about to investigate."""
        sources = [u.source_name.lower() for u in cluster.units if u.source_name]
        source_set = set(sources)
        parts: list[str] = []
        if any("velocity" in s or "amount" in s for s in source_set):
            parts.append("unusual transaction speeds or amounts")
        if any("device" in s or "fingerprint" in s for s in source_set):
            parts.append("suspicious device activity")
        if any("geographic" in s or "ip" in s for s in source_set):
            parts.append("geographic anomalies")
        if any("identity" in s or "recipient" in s for s in source_set):
            parts.append("identity or recipient concerns")
        if any("trading" in s for s in source_set):
            parts.append("unusual trading behavior")
        if not parts:
            parts.append("suspicious activity")
        signal_desc = " and ".join(parts[:2])
        return (
            f"Investigating a group of {events} events across {accounts} accounts "
            f"showing {signal_desc}. The agent will query the database and "
            f"cross-reference known fraud typologies."
        )
