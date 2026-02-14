"""KMeans clustering tool for background audit agent."""

from __future__ import annotations

import logging

import numpy as np
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from app.data.vector.store import get_collection

logger = logging.getLogger(__name__)


class KMeansInput(BaseModel):
    k: int = Field(ge=2, le=10, description="Number of clusters (2-10)")


class KMeansClusterTool(BaseTool):
    """Run KMeans on cached embeddings and compare with HDBSCAN results."""

    name: str = "kmeans_cluster"
    description: str = (
        "Run KMeans clustering on the current run's embeddings with a "
        "specified k value. Returns cluster labels, silhouette score, "
        "inertia, and cluster sizes. Use to compare against the default "
        "HDBSCAN clustering and check if a different k reveals sub-patterns."
    )
    args_schema: type[BaseModel] = KMeansInput

    def _run(self, k: int) -> str:
        return self._cluster(k)

    async def _arun(self, k: int) -> str:
        return self._cluster(k)

    def _cluster(self, k: int) -> str:
        try:
            collection = get_collection()
            result = collection.get(include=["embeddings"])
            embeddings = result.get("embeddings")
        except Exception as exc:
            return f"Failed to fetch embeddings from ChromaDB: {exc}"

        if not embeddings:
            return "No embeddings available in ChromaDB collection."

        arr = np.array(embeddings)
        if len(arr) < k:
            return f"Only {len(arr)} samples — need at least k={k}."

        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(arr)
        sil = float(silhouette_score(arr, labels)) if k < len(arr) else 0.0

        sizes = {}
        for label in labels:
            sizes[int(label)] = sizes.get(int(label), 0) + 1

        return (
            f"KMeans(k={k}): silhouette={sil:.3f}, "
            f"inertia={km.inertia_:.1f}, "
            f"cluster_sizes={sizes}"
        )
