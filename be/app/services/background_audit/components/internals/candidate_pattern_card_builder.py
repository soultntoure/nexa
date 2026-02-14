"""Pattern-card construction — async IO wrapper around core extraction."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.background_audit.pattern_card import (
    as_text,
    extract_agent_fields,
    extract_sql_query,
    friendly_source_label,
)
from app.services.background_audit.components.embed_cluster import ClusterData

logger = logging.getLogger(__name__)


async def build_pattern_card(
    cluster: ClusterData,
    agent: Any | None,
    emit: Any | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build candidate pattern card using the LLM agent when available."""
    raw_sources = sorted({as_text(unit.source_name) for unit in cluster.units if as_text(unit.source_name)})
    friendly_sources = [friendly_source_label(source) for source in raw_sources]
    card: dict[str, Any] = {
        "cluster_id": cluster.cluster_id,
        "novelty": cluster.novelty.status,
        "source_types": friendly_sources,
        "source_types_raw": raw_sources,
        "support_events": len(cluster.units),
        "support_accounts": len({str(unit.withdrawal_id) for unit in cluster.units}),
        "agent_fallback_used": agent is None,
        "formal_pattern_name": "Unknown",
        "plain_language": "",
        "analyst_notes": "",
        "limitations": "",
        "uncertainty": "",
        "clustering_notes": "",
        "sql_findings": [],
        "web_references": [],
        "evidence_units": [],
        "tool_trace": [],
    }
    tool_trace: list[dict[str, Any]] = []

    if not agent:
        return card, tool_trace

    try:
        start = time.monotonic()
        summary_input = "\n".join(unit.text_masked[:200] for unit in cluster.units[:5])
        result, trace = await agent.synthesize_candidate(summary_input)
        card["agent_duration_s"] = round(time.monotonic() - start, 2)
        tool_trace = trace
        extract_agent_fields(card, result, trace)
        if emit and trace:
            await _emit_tool_trace(emit, trace, cluster.cluster_id)
    except Exception:
        logger.warning("Agent synthesis failed, using template", exc_info=True)
        card["agent_fallback_used"] = True

    card["tool_trace"] = tool_trace
    return card, tool_trace


def _narrate_tool_call(tool_name: str, args_preview: str) -> str:
    """Generate a plain-English narration for what the tool call is doing."""
    lower_args = args_preview.lower()
    if tool_name.startswith("sql"):
        if "count" in lower_args and "withdraw" in lower_args:
            return "Checking how many withdrawals these accounts made recently..."
        if "device" in lower_args or "fingerprint" in lower_args:
            return "Looking for shared devices across flagged accounts..."
        if "ip" in lower_args:
            return "Checking if these accounts connected from the same IP addresses..."
        if "payment_method" in lower_args or "card" in lower_args:
            return "Investigating shared payment methods across accounts..."
        if "customer" in lower_args and "group by" in lower_args:
            return "Analyzing account relationships and transaction patterns..."
        return "Running a database query to verify the hypothesis..."
    if "web" in tool_name or "search" in tool_name or "tavily" in tool_name:
        return "Searching for known fraud typologies that match this pattern..."
    if "kmeans" in tool_name or "cluster" in tool_name:
        return "Re-analyzing the cluster to check for sub-patterns..."
    return "Processing additional analysis..."


def _narrate_tool_result(tool_name: str, result_preview: str) -> str | None:
    """Generate a plain-English insight from a tool result, or None if not useful."""
    result = result_preview.strip()
    if not result or len(result) < 10:
        return None
    if tool_name.startswith("sql"):
        if "0 rows" in result.lower() or result.strip() == "[]":
            return "No matching records found — this reduces suspicion for this angle."
        return f"Database returned results that the agent is now analyzing."
    if "web" in tool_name or "search" in tool_name or "tavily" in tool_name:
        return "Found relevant fraud research to cross-reference with this pattern."
    return None


async def _emit_tool_trace(
    emit: Any,
    trace: list[dict[str, Any]],
    cluster_id: str,
) -> None:
    for tool_call in trace:
        tool_name = as_text(tool_call.get("tool"))
        if not tool_name:
            continue
        query_preview = (
            extract_sql_query(tool_call.get("args_preview"))
            if tool_name.startswith("sql")
            else as_text(tool_call.get("args_preview"))
        )
        narration = _narrate_tool_call(tool_name, query_preview)
        await emit(
            "agent_tool",
            {
                "title": narration,
                "phase": "investigate",
                "narration": narration,
                "tool_name": tool_name,
                "args_preview": query_preview[:300],
                "result_preview": as_text(tool_call.get("result_preview"))[:300],
                "cluster_id": cluster_id,
            },
        )
        result_preview = as_text(tool_call.get("result_preview"))
        insight = _narrate_tool_result(tool_name, result_preview)
        if insight:
            await emit(
                "insight",
                {
                    "title": insight,
                    "phase": "investigate",
                    "narration": insight,
                    "cluster_id": cluster_id,
                    "tool_name": tool_name,
                },
            )
