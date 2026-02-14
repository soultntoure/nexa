"""Candidate signature construction and duplicate matching."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.core.background_audit.text_normalization import (
    as_text,
    extract_theme_set,
    normalize_sql_findings,
    normalize_text,
    normalize_web_references,
    tokenize_keywords,
)


@dataclass(frozen=True)
class CandidateSignature:
    """Compact signature used for in-memory candidate dedupe."""

    candidate_id: str
    normalized_name: str
    keyword_set: frozenset[str]
    theme_set: frozenset[str]
    centroid: tuple[float, ...]


def build_candidate_signature(
    *,
    candidate_id: str,
    pattern_card: dict[str, Any],
    centroid: tuple[float, ...],
) -> CandidateSignature:
    """Build a concise, deterministic signature for dedupe matching."""
    normalized_name = normalize_text(pattern_card.get("formal_pattern_name"))
    signature_text = _compose_signature_text(pattern_card)
    return CandidateSignature(
        candidate_id=candidate_id,
        normalized_name=normalized_name,
        keyword_set=tokenize_keywords(signature_text),
        theme_set=extract_theme_set(signature_text),
        centroid=centroid,
    )


def merge_signatures(
    base: CandidateSignature,
    incoming: CandidateSignature,
    *,
    base_support_events: int,
    incoming_support_events: int,
) -> CandidateSignature:
    """Merge deduped signatures to keep future matches stable."""
    name = base.normalized_name
    if name in {"", "unknown", "novel pattern"} and incoming.normalized_name:
        name = incoming.normalized_name

    return CandidateSignature(
        candidate_id=base.candidate_id,
        normalized_name=name,
        keyword_set=base.keyword_set | incoming.keyword_set,
        theme_set=base.theme_set | incoming.theme_set,
        centroid=_blend_centroids(
            base.centroid, incoming.centroid,
            base_weight=base_support_events,
            incoming_weight=incoming_support_events,
        ),
    )


def match_duplicate_candidate(
    existing_signatures: dict[str, CandidateSignature],
    incoming_signature: CandidateSignature,
) -> tuple[str | None, str | None, dict[str, float]]:
    """Find best duplicate candidate. Returns (id, reason, metrics)."""
    best_id: str | None = None
    best_reason: str | None = None
    best_metrics: dict[str, float] = {}
    best_composite = 0.0

    for cid, existing in existing_signatures.items():
        reason, metrics = _score_pair(existing, incoming_signature)
        if reason is None:
            continue
        composite = metrics["token_similarity"] + metrics["centroid_similarity"]
        if composite > best_composite:
            best_composite = composite
            best_id = cid
            best_reason = reason
            best_metrics = metrics

    return best_id, best_reason, best_metrics


def _score_pair(
    existing: CandidateSignature,
    incoming: CandidateSignature,
) -> tuple[str | None, dict[str, float]]:
    """Score a pair and return (reason, metrics)."""
    token_sim = _jaccard(existing.keyword_set, incoming.keyword_set)
    theme_ovlp = _overlap(existing.theme_set, incoming.theme_set)
    centroid_sim = _cosine(existing.centroid, incoming.centroid)
    same_name = (
        existing.normalized_name
        and existing.normalized_name == incoming.normalized_name
        and existing.normalized_name != "unknown"
    )
    reason = _classify(same_name, token_sim, theme_ovlp, centroid_sim)
    metrics = {
        "token_similarity": round(token_sim, 4),
        "theme_overlap": round(theme_ovlp, 4),
        "centroid_similarity": round(centroid_sim, 4),
        "same_name": 1.0 if same_name else 0.0,
    }
    return reason, metrics


def _classify(
    same_name: bool,
    token_sim: float,
    theme_ovlp: float,
    centroid_sim: float,
) -> str | None:
    if same_name and (token_sim >= 0.15 or theme_ovlp >= 0.30 or centroid_sim >= 0.70):
        return "same_pattern_name"
    if centroid_sim >= 0.80:
        return "high_embedding_overlap"
    if token_sim >= 0.35 and centroid_sim >= 0.60:
        return "high_text_and_embedding_overlap"
    if theme_ovlp >= 0.50 and (centroid_sim >= 0.55 or token_sim >= 0.25):
        return "high_theme_overlap"
    return None


def _compose_signature_text(card: dict[str, Any]) -> str:
    parts = [
        as_text(card.get("formal_pattern_name")),
        as_text(card.get("plain_language")),
        as_text(card.get("analyst_notes")),
        as_text(card.get("limitations")),
        as_text(card.get("uncertainty")),
        as_text(card.get("clustering_notes")),
    ]
    for f in normalize_sql_findings(card.get("sql_findings")):
        parts.extend([f.get("query", ""), f.get("result", "")])
    for r in normalize_web_references(card.get("web_references")):
        parts.extend([r.get("title", ""), r.get("snippet", "")])
    return normalize_text(" ".join(p for p in parts if p))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _blend_centroids(
    base: tuple[float, ...],
    incoming: tuple[float, ...],
    base_weight: int,
    incoming_weight: int,
) -> tuple[float, ...]:
    if not base:
        return incoming
    if not incoming or len(base) != len(incoming):
        return base
    left = max(base_weight, 1)
    right = max(incoming_weight, 1)
    total = left + right
    return tuple((base[i] * left + incoming[i] * right) / total for i in range(len(base)))
