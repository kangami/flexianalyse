"""
Embedder — generates OpenAI embeddings for extracted chunks.
Handles batching to stay within OpenAI rate limits.
"""

import logging
import os
import time
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
EMBEDDING_BATCH_SIZE = 100  # OpenAI max per request


class Embedder:
    """Generates embeddings for text chunks using OpenAI."""

    def __init__(self):
        self._client = OpenAI()

    def embed_chunks(self, texts: list[str]) -> list[Optional[list[float]]]:
        """
        Embed a list of texts in batches.
        Returns list of embeddings in same order as input.
        """
        if not texts:
            return []

        embeddings = []
        batches = [
            texts[i:i + EMBEDDING_BATCH_SIZE]
            for i in range(0, len(texts), EMBEDDING_BATCH_SIZE)
        ]

        for batch_idx, batch in enumerate(batches):
            try:
                response = self._client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                    dimensions=EMBEDDING_DIMENSIONS,
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                logger.info(
                    f"Embedded batch {batch_idx + 1}/{len(batches)} "
                    f"({len(batch)} chunks)"
                )

                # Rate limit safety — 500ms between batches
                if batch_idx < len(batches) - 1:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Embedding batch {batch_idx} failed: {e}", exc_info=True)
                # Return None for failed batch items
                embeddings.extend([None] * len(batch))

        return embeddings

    def embed_single(self, text: str) -> Optional[list[float]]:
        """Embed a single text — used for query embedding."""
        results = self.embed_chunks([text])
        return results[0] if results else None