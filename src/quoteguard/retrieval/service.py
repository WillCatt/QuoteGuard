"""Composite retrieval service."""

from __future__ import annotations

from pathlib import Path

from quoteguard.ingestion.embedder import EmbedderBackend, HashingEmbedder, get_embedder
from quoteguard.ingestion.models import Chunk
from quoteguard.retrieval.fusion import reciprocal_rank_fusion
from quoteguard.retrieval.reranker import LexicalReranker
from quoteguard.retrieval.sparse import SparseRetriever
from quoteguard.retrieval.vector_store import VectorStoreBackend, get_vector_store


class RetrievalService:
    def __init__(
        self,
        chunks: list[Chunk],
        store_path: Path,
        *,
        embedder_backend: EmbedderBackend | None = None,
        vector_store_backend: VectorStoreBackend | None = None,
    ):
        self.chunks = chunks
        self.embedder = get_embedder(embedder_backend)
        self.vector_store = get_vector_store(
            store_path=store_path,
            embedder=self.embedder,
            backend=vector_store_backend,
        )
        if chunks:
            self.vector_store.upsert_chunks(chunks)
        self.sparse = SparseRetriever(chunks)
        self.reranker = LexicalReranker()

    def query(self, text: str, k: int = 5, filters: dict[str, str] | None = None) -> list[dict]:
        dense = self.vector_store.query(text, k=max(10, k), filters=filters)
        sparse = self.sparse.query(text, k=max(10, k), filters=filters)
        fused = reciprocal_rank_fusion([dense, sparse])
        return self.reranker.rerank(text, fused, top_k=k)
