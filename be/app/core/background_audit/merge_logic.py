"""Candidate dedupe metadata and merge — pure data transformations."""

from __future__ import annotations

from typing import Any

from app.core.background_audit.text_normalization import (
    as_text,
    dedupe_dict_rows,
    is_skippable_pattern,
    normalize_sql_findings,
    normalize_web_references,
    safe_float,
)


def should_skip_pattern(pattern_name: str) -> bool:
    """Filter out meta-pattern labels that should not create candidates."""
    return is_skippable_pattern(pattern_name)


def initialize_dedupe_metadata(
    *,
    pattern_card: dict[str, Any],
    candidate_id: str,
    cluster_id: str,
    evidence_score: float,
) -> None:
    """Ensure dedupe list keys exist, then register the current candidate."""
    _ensure_dedupe_lists(pattern_card)
    _register_candidate(pattern_card, candidate_id, cluster_id, evidence_score)


def merge_candidate_card(
    pattern_card: dict[str, Any],
    new_card: dict[str, Any],
    *,
    incoming_candidate_id: str,
    cluster_id: str,
    dedupe_reason: str,
    similarity_metrics: dict[str, float],
    incoming_evidence_quality: float,
) -> None:
    """Merge duplicate pattern data into an existing candidate's card."""
    _merge_plain_language_variants(pattern_card, new_card)
    pattern_card["dedupe_reasons"].append({
        "reason": dedupe_reason,
        "merged_candidate_id": incoming_candidate_id,
        "merged_cluster_id": cluster_id,
        "similarity": similarity_metrics,
    })
    pattern_card["evidence_quality_max"] = max(
        safe_float(pattern_card.get("evidence_quality_max"), 0.0),
        incoming_evidence_quality,
    )
    pattern_card["source_types"] = _merge_source_types(pattern_card, new_card)
    pattern_card["evidence_units"] = _merge_field(pattern_card, new_card, "evidence_units", keys=("type", "summary", "result", "query"), cap=5)
    pattern_card["sql_findings"] = _merge_field(pattern_card, new_card, "sql_findings", keys=("query", "result"), cap=3, normalizer=normalize_sql_findings)
    pattern_card["web_references"] = _merge_field(pattern_card, new_card, "web_references", keys=("url", "title", "snippet"), cap=2, normalizer=normalize_web_references)
    _promote_formal_pattern_name(pattern_card, new_card)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ensure_dedupe_lists(pattern_card: dict[str, Any]) -> None:
    """Initialize any missing dedupe list keys to empty lists."""
    for key in ("merged_clusters", "deduped_candidate_ids", "dedupe_reasons", "dedupe_variant_plain_language"):
        if not isinstance(pattern_card.get(key), list):
            pattern_card[key] = []


def _register_candidate(
    pattern_card: dict[str, Any],
    candidate_id: str,
    cluster_id: str,
    evidence_score: float,
) -> None:
    """Append candidate/cluster ids and update aggregate quality stats."""
    merged = pattern_card["merged_clusters"]
    deduped = pattern_card["deduped_candidate_ids"]

    if cluster_id not in merged:
        merged.append(cluster_id)
    if candidate_id not in deduped:
        deduped.append(candidate_id)

    pattern_card["evidence_quality_max"] = max(
        safe_float(pattern_card.get("evidence_quality_max"), 0.0),
        evidence_score,
    )
    pattern_card["deduped_cluster_count"] = max(len(merged), 1)


def _merge_plain_language_variants(
    pattern_card: dict[str, Any], new_card: dict[str, Any],
) -> None:
    existing_plain = as_text(pattern_card.get("plain_language"))
    incoming_plain = as_text(new_card.get("plain_language"))
    variants = pattern_card["dedupe_variant_plain_language"]
    if existing_plain and existing_plain not in variants:
        variants.append(existing_plain)
    if incoming_plain and incoming_plain not in variants:
        variants.append(incoming_plain)


def _merge_source_types(
    pattern_card: dict[str, Any], new_card: dict[str, Any],
) -> list[str]:
    existing = pattern_card.get("source_types") or []
    incoming = new_card.get("source_types") or []
    return list(dict.fromkeys(
        as_text(s) for s in [*existing, *incoming] if as_text(s)
    ))


def _merge_field(
    pattern_card: dict[str, Any],
    new_card: dict[str, Any],
    field: str,
    *,
    keys: tuple[str, ...],
    cap: int,
    normalizer: Any = None,
) -> list[dict[str, Any]]:
    """Merge a list field from two cards: normalize, dedupe by key fields, cap."""
    if normalizer:
        existing = normalizer(pattern_card.get(field))
        incoming = normalizer(new_card.get(field))
    else:
        existing = [r for r in (pattern_card.get(field) or []) if isinstance(r, dict)]
        incoming = [r for r in (new_card.get(field) or []) if isinstance(r, dict)]

    merged = dedupe_dict_rows(
        existing, incoming,
        key_builder=lambda row: "|".join(as_text(row.get(k)) for k in keys),
    )
    return merged[:cap]


def _promote_formal_pattern_name(
    pattern_card: dict[str, Any], new_card: dict[str, Any],
) -> None:
    incoming = as_text(new_card.get("formal_pattern_name"))
    existing = as_text(pattern_card.get("formal_pattern_name"))
    if incoming and incoming.lower() != "unknown" and existing.lower() in {"", "unknown"}:
        pattern_card["formal_pattern_name"] = incoming
