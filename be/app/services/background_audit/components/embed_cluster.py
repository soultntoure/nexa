"""Embed + cluster component — vectorize text units and run HDBSCAN."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.background_audit.pattern_analysis import (
    NoveltyResult,
    assign_clusters,
    compute_centroid,
    detect_novelty,
)
from app.data.db.models.audit_text_unit import AuditTextUnit
from app.data.db.repositories.audit_unit_repository import AuditUnitRepository
from app.data.vector import embeddings as emb_module
from app.data.vector import store as vec_store

logger = logging.getLogger(__name__)


@dataclass
class ClusterData:
    """Cluster with its units, centroid, and novelty info."""

    cluster_id: str
    units: list[AuditTextUnit]
    centroid: list[float]
    novelty: NoveltyResult


async def embed_and_cluster(
    units: list[AuditTextUnit],
    session_factory: async_sessionmaker[AsyncSession],
    min_cluster_size: int = 8,
    min_samples: int | None = 4,
    merge_similarity: float = 0.90,
    normalize_embeddings: bool = True,
) -> list[ClusterData]:
    """Embed units, upsert to ChromaDB, run clustering."""
    if not units:
        return []

    texts = [u.text_masked for u in units]
    unit_ids = [u.unit_id for u in units]

    embeddings = await emb_module.embed_texts(texts)
    logger.info("Embedded %d units", len(embeddings))

    metadatas = [
        {"source_type": u.source_type, "source_name": u.source_name}
        for u in units
    ]
    vec_store.upsert_vectors(unit_ids, embeddings, metadatas)

    async with session_factory() as session:
        repo = AuditUnitRepository(session)
        await repo.mark_vector_status(unit_ids, "embedded")

    cluster_result = assign_clusters(
        embeddings,
        min_cluster_size=max(min_cluster_size, 2),
        min_samples=min_samples,
        normalize=normalize_embeddings,
        merge_similarity=merge_similarity,
    )
    logger.info(
        "Clustering: %d clusters, %d noise (min_size=%d, min_samples=%s, merge_similarity=%.2f)",
        cluster_result.n_clusters,
        cluster_result.noise_count,
        max(min_cluster_size, 2),
        str(min_samples),
        merge_similarity,
    )

    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(cluster_result.cluster_labels):
        if label == -1:
            continue
        cluster_map.setdefault(label, []).append(idx)

    clusters: list[ClusterData] = []
    for label, indices in cluster_map.items():
        cluster_units = [units[i] for i in indices]
        cluster_embeddings = [embeddings[i] for i in indices]
        centroid = compute_centroid(cluster_embeddings)
        novelty = detect_novelty(centroid, {})

        clusters.append(ClusterData(
            cluster_id=f"cluster_{label}",
            units=cluster_units,
            centroid=centroid,
            novelty=novelty,
        ))

    return clusters
