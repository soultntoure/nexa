"""
ChromaDB vector store for background audit and fraud patterns.

Contains:
- get_client() — persistent ChromaDB HTTP client
- upsert_vectors() — add/update vectors in collection
- query_similar() — find similar vectors
- retire_vectors() — remove stale vectors
"""

from __future__ import annotations

import logging
from typing import Any

import chromadb

from app.config import get_settings

logger = logging.getLogger(__name__)

AUDIT_COLLECTION = "background_audit_stage1"

_client: chromadb.HttpClient | None = None


def get_client() -> chromadb.HttpClient:
    """Get or create ChromaDB HTTP client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.HttpClient(
            host=settings.CHROMADB_HOST,
            port=settings.CHROMADB_PORT,
        )
    return _client


def get_collection(
    name: str = AUDIT_COLLECTION,
) -> chromadb.Collection:
    """Get or create a ChromaDB collection."""
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_vectors(
    ids: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]] | None = None,
    collection_name: str = AUDIT_COLLECTION,
) -> None:
    """Add or update vectors in the collection."""
    if not ids:
        return
    collection = get_collection(collection_name)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info("Upserted %d vectors to %s", len(ids), collection_name)


def query_similar(
    query_embedding: list[float],
    n_results: int = 10,
    collection_name: str = AUDIT_COLLECTION,
) -> dict[str, Any]:
    """Find similar vectors by cosine similarity."""
    collection = get_collection(collection_name)
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )


def retire_vectors(
    ids: list[str],
    collection_name: str = AUDIT_COLLECTION,
) -> None:
    """Remove vectors from collection."""
    if not ids:
        return
    collection = get_collection(collection_name)
    collection.delete(ids=ids)
    logger.info("Retired %d vectors from %s", len(ids), collection_name)
