"""Pure pattern-card field extraction from agent output."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from app.core.background_audit.text_normalization import (
    as_text,
    dedupe_dict_rows,
    normalize_sql_findings,
    normalize_web_references,
)

_SOURCE_LABELS = {
    "constellation_analysis": "Triage Constellation",
    "cross_account": "Cross-Account Analysis",
    "financial_behavior": "Financial Behavior Analysis",
    "identity_access": "Identity & Access Analysis",
    "triage": "Triage Analysis",
    "investigator": "Investigator Finding",
    "supporting": "Supporting Evidence",
    "sql_trace": "SQL Trace",
    "web_trace": "Web Trace",
}


def friendly_source_label(source: Any) -> str:
    """Map raw source name to a human-friendly label."""
    raw = str(source or "").strip()
    if not raw:
        return "Evidence"

    normalized = raw.lower().strip()
    if normalized in _SOURCE_LABELS:
        return _SOURCE_LABELS[normalized]

    cleaned = re.sub(r"[_\-]+", " ", raw)
    return " ".join(token.capitalize() for token in cleaned.split())


def extract_agent_fields(
    card: dict[str, Any],
    result: dict[str, Any],
    trace: list[dict[str, Any]],
) -> None:
    """Extract normalized fields from agent output into a pattern card."""
    card["formal_pattern_name"] = as_text(result.get("formal_pattern_name")) or "Unknown"
    card["plain_language"] = as_text(result.get("plain_language"))
    card["analyst_notes"] = as_text(result.get("analyst_notes"))
    card["limitations"] = as_text(result.get("limitations"))
    card["uncertainty"] = as_text(result.get("uncertainty"))
    card["clustering_notes"] = as_text(result.get("clustering_notes"))
    sql_from_result = normalize_sql_findings(result.get("sql_findings", []))
    sql_from_trace = trace_sql_findings(trace)
    card["sql_findings"] = _compact_sql_findings(dedupe_dict_rows(
        sql_from_result,
        sql_from_trace,
        key_builder=lambda row: "|".join([
            as_text(row.get("query")),
            as_text(row.get("result")),
        ]),
    ))
    card["web_references"] = normalize_web_references(result.get("web_references", []))


_MAX_SQL_FINDINGS = 6
_SQL_VALUE_LIMIT = 200


def _compact_sql_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    """Cap count, truncate values, drop redundant summary fields."""
    compacted: list[dict[str, str]] = []
    for f in findings[:_MAX_SQL_FINDINGS]:
        compacted.append({
            "query": as_text(f.get("query"))[:_SQL_VALUE_LIMIT],
            "result": as_text(f.get("result"))[:_SQL_VALUE_LIMIT],
        })
    return compacted


def trace_sql_findings(trace: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract SQL findings from agent tool trace."""
    findings: list[dict[str, str]] = []
    for tool_call in trace:
        tool_name = as_text(tool_call.get("tool"))
        if not tool_name.startswith("sql"):
            continue
        query = extract_sql_query(tool_call.get("args_preview"))
        result = as_text(tool_call.get("result_preview"))
        if not query and not result:
            continue
        findings.append({"query": query, "result": result})
    return findings


def extract_sql_query(args_preview: Any) -> str:
    """Parse SQL query from various agent output formats."""
    if isinstance(args_preview, dict):
        return as_text(args_preview.get("query"))

    raw = as_text(args_preview)
    if not raw:
        return ""

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(raw)
            if isinstance(parsed, dict):
                query = as_text(parsed.get("query"))
                if query:
                    return query
        except Exception:
            continue

    match = re.search(
        r"[\"']query[\"']\s*:\s*[\"'](.+?)[\"']", raw, re.IGNORECASE | re.DOTALL,
    )
    if match:
        return as_text(match.group(1))

    return raw
