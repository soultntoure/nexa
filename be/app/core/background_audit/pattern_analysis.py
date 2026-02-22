"""Pattern analysis utilities for background audit clustering and scoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import hdbscan
import numpy as np

logger = logging.getLogger(__name__)

# Cosine similarity thresholds for novelty classification
COSINE_THRESHOLD = 0.82
DRIFT_THRESHOLD = 0.70
EXISTING_THRESHOLD = 0.82
DEFAULT_CLUSTER_MERGE_SIMILARITY = 0.90

# Weights for calculate_candidate_quality — must sum to 1.0
_WEIGHT_CONFIDENCE = 0.35
_WEIGHT_SUPPORT = 0.25
_WEIGHT_IMPACT = 0.20
_WEIGHT_EVIDENCE = 0.20

# Normalization caps for support counts
_SUPPORT_EVENTS_CAP = 50.0
_SUPPORT_ACCOUNTS_CAP = 20.0
_SUPPORT_EVENTS_WEIGHT = 0.6
_SUPPORT_ACCOUNTS_WEIGHT = 0.4

# Rank score weights for rank_evidence
_RANK_WEIGHT_CONFIDENCE = 0.4
_RANK_WEIGHT_SCORE = 0.3
_RANK_WEIGHT_DIVERSITY = 0.3
_RANK_DIVERSITY_BONUS = 0.1


@dataclass
class ClusterResult:
    """Result of clustering operation."""

    cluster_labels: list[int]
    n_clusters: int
    noise_count: int


@dataclass(frozen=True)
class NoveltyResult:
    """Classification of a cluster's novelty."""

    status: str  # "new" | "drifted_existing" | "existing"
    matched_cluster_id: str | None
    similarity: float


def assign_clusters(
    embeddings: list[list[float]],
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    metric: str = "euclidean",
    cluster_selection_method: str = "eom",
    normalize: bool = True,
    merge_similarity: float | None = DEFAULT_CLUSTER_MERGE_SIMILARITY,
) -> ClusterResult:
    """Run HDBSCAN clustering on embedding vectors."""
    if not embeddings:
        return ClusterResult(cluster_labels=[], n_clusters=0, noise_count=0)

    if len(embeddings) < min_cluster_size:
        return ClusterResult(
            cluster_labels=[-1] * len(embeddings),
            n_clusters=0,
            noise_count=len(embeddings),
        )

    matrix = np.array(embeddings, dtype=float)
    if normalize:
        matrix = _normalize_matrix(matrix)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_method=cluster_selection_method,
    )
    labels = clusterer.fit_predict(matrix).tolist()

    if merge_similarity is not None and merge_similarity > 0:
        labels, merged_pairs = merge_similar_clusters(labels, embeddings, min_similarity=merge_similarity)
        if merged_pairs > 0:
            logger.info("Merged %d similar cluster pairs (similarity>=%.2f)", merged_pairs, merge_similarity)

    n_clusters = len(set(labels) - {-1})
    noise_count = labels.count(-1)

    logger.info(
        "Clustered %d vectors into %d clusters (%d noise, min_size=%d, min_samples=%s, normalize=%s)",
        len(embeddings), n_clusters, noise_count, min_cluster_size, str(min_samples), str(normalize),
    )
    return ClusterResult(cluster_labels=labels, n_clusters=n_clusters, noise_count=noise_count)


def assign_to_nearest_prototype(
    embedding: list[float],
    prototypes: dict[str, list[float]],
) -> tuple[str | None, float]:
    """Assign vector to nearest prototype if cosine sim >= threshold."""
    if not prototypes:
        return None, 0.0

    vec = np.array(embedding)
    best_id, best_sim = _find_best_match(vec, {k: np.array(v) for k, v in prototypes.items()})

    if best_sim >= COSINE_THRESHOLD:
        return best_id, best_sim
    return None, best_sim


def merge_similar_clusters(
    labels: list[int],
    embeddings: list[list[float]],
    min_similarity: float = DEFAULT_CLUSTER_MERGE_SIMILARITY,
) -> tuple[list[int], int]:
    """Merge cluster labels whose centroids are highly similar."""
    cluster_indices = _group_indices_by_cluster(labels)
    cluster_ids = sorted(cluster_indices)

    if len(cluster_ids) < 2:
        return labels, 0

    centroids = _compute_normalized_centroids(cluster_ids, cluster_indices, embeddings)
    parent, merged_pairs = _union_find_merge(cluster_ids, centroids, min_similarity)

    if merged_pairs == 0:
        return labels, 0

    remap = _build_remap(cluster_ids, parent)
    merged_labels = [-1 if label == -1 else remap[label] for label in labels]
    return merged_labels, merged_pairs


def compute_centroid(embeddings: list[list[float]]) -> list[float]:
    """Compute centroid of a set of embeddings."""
    return np.mean(embeddings, axis=0).tolist()


def detect_novelty(
    centroid: list[float],
    existing_centroids: dict[str, list[float]],
) -> NoveltyResult:
    """Compare a new cluster centroid against existing ones."""
    if not existing_centroids:
        return NoveltyResult(status="new", matched_cluster_id=None, similarity=0.0)

    vec = np.array(centroid)
    best_id, best_sim = _find_best_match(vec, {k: np.array(v) for k, v in existing_centroids.items()})

    if best_sim >= EXISTING_THRESHOLD:
        return NoveltyResult(status="existing", matched_cluster_id=best_id, similarity=best_sim)
    if best_sim >= DRIFT_THRESHOLD:
        return NoveltyResult(status="drifted_existing", matched_cluster_id=best_id, similarity=best_sim)
    return NoveltyResult(status="new", matched_cluster_id=None, similarity=best_sim)


def calculate_candidate_quality(
    confidence: float,
    support_events: int,
    support_accounts: int,
    evidence_quality: float,
    impact_estimate: float = 0.5,
) -> float:
    """Weighted quality score combining confidence, support, impact, and evidence."""
    support_norm = min(support_events / _SUPPORT_EVENTS_CAP, 1.0)
    account_norm = min(support_accounts / _SUPPORT_ACCOUNTS_CAP, 1.0)
    support_score = _SUPPORT_EVENTS_WEIGHT * support_norm + _SUPPORT_ACCOUNTS_WEIGHT * account_norm

    return round(
        _WEIGHT_CONFIDENCE * confidence
        + _WEIGHT_SUPPORT * support_score
        + _WEIGHT_IMPACT * impact_estimate
        + _WEIGHT_EVIDENCE * evidence_quality,
        4,
    )


def meets_quality_gate(
    support_events: int,
    support_accounts: int,
    confidence: float,
    min_events: int = 5,
    min_accounts: int = 2,
    min_confidence: float = 0.50,
) -> bool:
    """Check if cluster meets minimum thresholds for candidacy."""
    return (
        support_events >= min_events
        and support_accounts >= min_accounts
        and confidence >= min_confidence
    )


def rank_evidence(
    units: list[dict[str, Any]],
    max_items: int = 5,
) -> list[dict[str, Any]]:
    """Rank evidence by confidence + account diversity + signal strength.

    Returns new dicts — does not mutate the input units.
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    seen_accounts: set[str] = set()

    for unit in units:
        conf = unit.get("confidence") or 0.5
        score = unit.get("score") or 0.0
        wid = str(unit.get("withdrawal_id", ""))
        diversity_bonus = _RANK_DIVERSITY_BONUS if wid not in seen_accounts else 0.0
        seen_accounts.add(wid)
        rank_score = (
            _RANK_WEIGHT_CONFIDENCE * conf
            + _RANK_WEIGHT_SCORE * score
            + _RANK_WEIGHT_DIVERSITY * diversity_bonus
        )
        scored.append((rank_score, unit))

    scored.sort(key=lambda row: row[0], reverse=True)

    return [
        {**unit, "rank": idx, "rank_score": round(rank_score, 4)}
        for idx, (rank_score, unit) in enumerate(scored[:max_items])
    ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _find_best_match(
    vec: np.ndarray,
    candidates: dict[str, np.ndarray],
) -> tuple[str | None, float]:
    """Return the id and cosine similarity of the closest candidate vector."""
    best_id: str | None = None
    best_sim = 0.0
    for cid, cvec in candidates.items():
        sim = _cosine_similarity(vec, cvec)
        if sim > best_sim:
            best_sim = sim
            best_id = cid
    return best_id, best_sim


def _group_indices_by_cluster(labels: list[int]) -> dict[int, list[int]]:
    """Map each cluster label to the list of embedding indices it contains."""
    groups: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        if label != -1:
            groups.setdefault(label, []).append(idx)
    return groups


def _compute_normalized_centroids(
    cluster_ids: list[int],
    cluster_indices: dict[int, list[int]],
    embeddings: list[list[float]],
) -> dict[int, np.ndarray]:
    """Compute and L2-normalize the centroid for each cluster."""
    centroids: dict[int, np.ndarray] = {}
    for cid in cluster_ids:
        vectors = [embeddings[i] for i in cluster_indices[cid]]
        centroid = np.array(compute_centroid(vectors), dtype=float)
        centroids[cid] = _normalize_vector(centroid)
    return centroids


def _union_find_merge(
    cluster_ids: list[int],
    centroids: dict[int, np.ndarray],
    min_similarity: float,
) -> tuple[dict[int, int], int]:
    """Union-find: merge clusters whose centroids exceed the similarity threshold."""
    parent = {cid: cid for cid in cluster_ids}

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]  # path compression
            node = parent[node]
        return node

    def union(left: int, right: int) -> bool:
        root_left, root_right = find(left), find(right)
        if root_left == root_right:
            return False
        parent[root_right] = root_left
        return True

    merged_pairs = 0
    for idx, left_id in enumerate(cluster_ids):
        for right_id in cluster_ids[idx + 1:]:
            sim = _cosine_similarity(centroids[left_id], centroids[right_id])
            if sim >= min_similarity and union(left_id, right_id):
                merged_pairs += 1

    return parent, merged_pairs


def _build_remap(cluster_ids: list[int], parent: dict[int, int]) -> dict[int, int]:
    """Assign compact sequential labels after union-find."""
    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    root_to_label: dict[int, int] = {}
    remap: dict[int, int] = {}
    next_label = 0
    for cid in cluster_ids:
        root = find(cid)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        remap[cid] = root_to_label[root]
    return remap


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector if norm == 0.0 else vector / norm


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms
