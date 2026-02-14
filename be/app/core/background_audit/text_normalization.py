"""Shared text and reference normalization helpers for candidates."""

from __future__ import annotations

import re
from typing import Any, Callable

_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "also",
    "same",
    "fraud",
    "pattern",
    "accounts",
    "account",
}

_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shared_device": ("shared device", "device fingerprint", "same device"),
    "shared_ip": ("shared ip", "same network", "same ip"),
    "shared_recipient": ("same recipient", "same bank account", "payout recipient"),
    "pass_through": (
        "deposit and immediately withdraw",
        "immediately attempting to withdraw",
        "little to no trading",
        "without trading",
    ),
    "stolen_cards": ("stolen card", "carding", "failed card"),
    "money_laundering": ("money laundering", "wash", "clean funds"),
}

_SKIP_PATTERNS = {
    "constellation_analysis",
    "identity_access",
    "cross_account",
    "financial_behavior",
    "unknown",
}


def as_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_text(value: Any) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", as_text(value).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tokenize_keywords(text: str) -> frozenset[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text)
    return frozenset(token for token in tokens if token not in _STOP_WORDS)


def extract_theme_set(text: str) -> frozenset[str]:
    themes: set[str] = set()
    for theme, keywords in _THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            themes.add(theme)
    return frozenset(themes)


def normalize_sql_findings(raw_findings: Any) -> list[dict[str, str]]:
    if not isinstance(raw_findings, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        query = as_text(item.get("query") or item.get("query_summary"))
        result = as_text(item.get("result") or item.get("result_summary"))
        if not query and not result:
            continue
        normalized.append(
            {
                "query": query,
                "result": result,
                "query_summary": query,
                "result_summary": result,
            }
        )
    return normalized


def normalize_web_references(raw_refs: Any) -> list[dict[str, str]]:
    if not isinstance(raw_refs, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in raw_refs:
        if not isinstance(item, dict):
            continue
        url = as_text(item.get("url"))
        title = as_text(item.get("title"))
        snippet = as_text(item.get("snippet") or item.get("relevance"))
        if not url and not title and not snippet:
            continue
        normalized.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
                "relevance": snippet,
            }
        )
    return normalized


def dedupe_dict_rows(
    existing_rows: list[dict[str, Any]],
    incoming_rows: list[dict[str, Any]],
    key_builder: Callable[[dict[str, Any]], str],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in [*existing_rows, *incoming_rows]:
        if not isinstance(row, dict):
            continue
        key = key_builder(row)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def is_skippable_pattern(pattern_name: str) -> bool:
    return normalize_text(pattern_name) in _SKIP_PATTERNS
