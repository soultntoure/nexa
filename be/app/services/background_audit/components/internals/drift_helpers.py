"""Helper functions for weight drift analysis phase."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.core.scoring import (
    APPROVE_THRESHOLD,
    BLOCK_THRESHOLD,
    INDICATOR_LABELS,
    INDICATOR_WEIGHTS,
)
from app.core.weight_drift import DriftSummary, OutlierResult


def humanize_indicator(name: str) -> str:
    """Convert raw indicator key to user-friendly label."""
    if name in INDICATOR_LABELS:
        return INDICATOR_LABELS[name]
    return name.replace("_", " ").title()


def extract_outlier_tuples(profiles: list) -> list[tuple[str, str, float]]:
    """Extract (customer_id, indicator, multiplier) tuples from profiles."""
    tuples: list[tuple[str, str, float]] = []
    for p in profiles:
        cid = str(p.customer_id)
        for name, entry in (p.indicator_weights or {}).items():
            m = entry.get("multiplier", 1.0) if isinstance(entry, dict) else 1.0
            tuples.append((cid, name, m))
    return tuples


def build_evidence_text(
    summary: DriftSummary, outliers: list[OutlierResult],
    countermeasures: list[dict], total: int,
) -> str:
    """Format drift data as text for the agent."""
    lines = [
        f"Total recalibrations: {total}",
        f"Unique customers: {summary.unique_customers}",
        "",
        "## Current System Configuration",
        f"Approve threshold: {APPROVE_THRESHOLD}",
        f"Block threshold: {BLOCK_THRESHOLD}",
        "Baseline indicator weights:",
    ]
    for name, weight in INDICATOR_WEIGHTS.items():
        lines.append(f"  - {humanize_indicator(name)}: {weight}")
    lines.append("")

    lines.append("## Indicator Drift Statistics")
    for ind in summary.indicators:
        label = humanize_indicator(ind.name)
        lines.append(
            f"- {label}: mean={ind.mean}, median={ind.median}, "
            f"std={ind.std}, trend={ind.trend}",
        )
    if outliers:
        lines.append(f"\nOutliers ({len(outliers)}):")
        for o in outliers[:10]:
            label = humanize_indicator(o.indicator_name)
            lines.append(
                f"  - {o.customer_id}/{label}: "
                f"{o.multiplier} (dev={o.deviation})",
            )
    if countermeasures:
        lines.append(f"\nCountermeasures ({len(countermeasures)}):")
        for c in countermeasures:
            label = humanize_indicator(c["indicator_name"])
            lines.append(f"  - [{c['severity']}] {label}: {c['issue']}")
    return "\n".join(lines)


def build_drift_data(
    summary: DriftSummary, outliers: list[OutlierResult],
    countermeasures: list[dict], total: int,
    window_start: str = "", window_end: str = "",
) -> dict[str, Any]:
    """Structure drift data for pattern_card embedding."""

    def _humanized_indicator(ind: dict) -> dict:
        return {**ind, "label": humanize_indicator(ind["name"])}

    def _humanized_outlier(out: dict) -> dict:
        return {**out, "indicator_label": humanize_indicator(out["indicator_name"])}

    def _humanized_countermeasure(cm: dict) -> dict:
        return {**cm, "indicator_label": humanize_indicator(cm["indicator_name"])}

    return {
        "indicators": [_humanized_indicator(asdict(i)) for i in summary.indicators],
        "outliers": [_humanized_outlier(asdict(o)) for o in outliers[:50]],
        "countermeasures": [_humanized_countermeasure(c) for c in countermeasures],
        "chart_data": {
            "labels": [humanize_indicator(i.name) for i in summary.indicators],
            "multipliers": [i.mean for i in summary.indicators],
            "trends": [
                {"rising": 1, "falling": -1}.get(i.trend, 0)
                for i in summary.indicators
            ],
        },
        "total_recalibrations": total,
        "window_start": window_start,
        "window_end": window_end,
    }


def _build_current_config() -> dict[str, Any]:
    """Snapshot current system configuration for the pattern card."""
    return {
        "approve_threshold": APPROVE_THRESHOLD,
        "block_threshold": BLOCK_THRESHOLD,
        "baseline_weights": {
            humanize_indicator(k): v for k, v in INDICATOR_WEIGHTS.items()
        },
    }


def build_pattern_card(
    agent_result: dict, drift_data: dict, tool_trace: list,
) -> dict[str, Any]:
    """Merge agent result with drift data into a pattern card."""
    return {
        "formal_pattern_name": "Weight Drift Analysis",
        "plain_language": agent_result.get("plain_language", "Weight drift summary"),
        "analyst_notes": agent_result.get("analyst_notes", ""),
        "limitations": agent_result.get("limitations", ""),
        "uncertainty": agent_result.get("uncertainty", ""),
        "recommendations": agent_result.get("recommendations", []),
        "sql_findings": agent_result.get("sql_findings", []),
        "web_references": agent_result.get("web_references", []),
        "clustering_notes": "",
        "drift_data": drift_data,
        "current_config": _build_current_config(),
        "tool_trace": tool_trace,
    }
