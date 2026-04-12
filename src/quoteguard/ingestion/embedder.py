"""Embedding helpers with a deterministic fallback implementation."""

from __future__ import annotations

import math
from collections import Counter
from enum import Enum
from typing import Iterable

from quoteguard.config.settings import settings
from quoteguard.ingestion.models import Chunk


class HashingEmbedder:
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        counts = Counter(text.lower().split())
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            slot = hash(token) % self.dimensions
            vector[slot] += float(count)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_chunks(self, chunks: Iterable[Chunk]) -> dict[str, list[float]]:
        return {chunk.chunk_id: self.embed_text(chunk.text) for chunk in chunks}


class EmbedderBackend(str, Enum):
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    HASHING = "hashing"


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or settings.embed_model
        self.model = SentenceTransformer(self.model_name)

    def _to_list(self, embeddings: object) -> list[list[float]]:
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [list(row) for row in embeddings]  # type: ignore[arg-type]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        encoded = self.model.encode(texts)
        return self._to_list(encoded)

    def embed_chunks(self, chunks: Iterable[Chunk]) -> dict[str, list[float]]:
        chunk_list = list(chunks)
        embeddings = self.embed_texts([chunk.text for chunk in chunk_list])
        return {chunk.chunk_id: vector for chunk, vector in zip(chunk_list, embeddings, strict=True)}


def available_embedder_backends() -> list[EmbedderBackend]:
    backends: list[EmbedderBackend] = []
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401

        backends.append(EmbedderBackend.SENTENCE_TRANSFORMERS)
    except ImportError:
        pass
    backends.append(EmbedderBackend.HASHING)
    return backends


def get_embedder(
    backend: EmbedderBackend | None = None,
    *,
    model_name: str | None = None,
) -> SentenceTransformerEmbedder | HashingEmbedder:
    selected = backend or available_embedder_backends()[0]
    if selected == EmbedderBackend.SENTENCE_TRANSFORMERS:
        try:
            return SentenceTransformerEmbedder(model_name=model_name)
        except ImportError:
            return HashingEmbedder()
    return HashingEmbedder()
