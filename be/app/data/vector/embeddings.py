"""
Embed text for similarity matching using Google Generative AI.

Contains:
- embed_texts() — batch embed with GoogleGenerativeAIEmbeddings
- embed_single() — embed one text
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/gemini-embedding-001"
TASK_TYPE = "CLUSTERING"
OUTPUT_DIM = 768
BATCH_SIZE = 100


def _get_embedder() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        task_type=TASK_TYPE,
        output_dimensionality=OUTPUT_DIM,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts, respecting batch size limit."""
    if not texts:
        return []

    embedder = _get_embedder()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_embeddings = await embedder.aembed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        logger.info("Embedded batch %d-%d of %d", i, i + len(batch), len(texts))

    return all_embeddings


async def embed_single(text: str) -> list[float]:
    """Embed a single text."""
    embedder = _get_embedder()
    return await embedder.aembed_query(text)
