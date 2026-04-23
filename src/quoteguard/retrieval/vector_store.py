"""Vector store wrapper with JSON persistence fallback."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from quoteguard.ingestion.embedder import HashingEmbedder
from quoteguard.ingestion.models import Chunk


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


class VectorStore:
    def __init__(self, store_path: Path, embedder: HashingEmbedder | None = None):
        self.store_path = store_path
        self.embedder = embedder or HashingEmbedder()
        self._rows: dict[str, dict] = {}
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if self.store_path.exists():
            self._load()

    def _load(self) -> None:
        for line in self.store_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            self._rows[row["chunk"]["chunk_id"]] = row

    def _persist(self) -> None:
        payload = "\n".join(json.dumps(row) for row in self._rows.values())
        self.store_path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        embeddings = self.embedder.embed_chunks(chunks)
        for chunk in chunks:
            self._rows[chunk.chunk_id] = {
                "chunk": chunk.model_dump(),
                "embedding": embeddings[chunk.chunk_id],
            }
        self._persist()

    def query(self, text: str, k: int = 5, filters: dict[str, str] | None = None) -> list[dict]:
        query_vector = self.embedder.embed_text(text)
        matches = []
        for row in self._rows.values():
            chunk = row["chunk"]
            if filters and any(chunk.get(key) != value for key, value in filters.items()):
                continue
            score = cosine_similarity(query_vector, row["embedding"])
            matches.append({"chunk": chunk, "score": score})
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:k]


class VectorStoreBackend(str, Enum):
    CHROMA = "chroma"
    JSONL = "jsonl"


class ChromaVectorStore:
    def __init__(self, store_path: Path, embedder: object, collection_name: str = "quoteguard_chunks"):
        import chromadb

        self.store_path = store_path
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(self.store_path))
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "source_pdf": chunk.source_pdf,
                "product_type": chunk.product_type,
                "section_path": " > ".join(chunk.section_path),
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]
        embeddings = self.embedder.embed_texts(documents) if hasattr(self.embedder, "embed_texts") else [
            self.embedder.embed_text(text) for text in documents
        ]
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, text: str, k: int = 5, filters: dict[str, str] | None = None) -> list[dict]:
        embedding = (
            self.embedder.embed_text(text)
            if hasattr(self.embedder, "embed_text")
            else self.embedder.embed_texts([text])[0]
        )
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=filters or None,
            include=["documents", "metadatas", "distances"],
        )
        rows = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, text_value, metadata, distance in zip(ids, docs, metadatas, distances, strict=False):
            rows.append(
                {
                    "chunk": {
                        "chunk_id": chunk_id,
                        "text": text_value,
                        "source_pdf": metadata.get("source_pdf", ""),
                        "product_type": metadata.get("product_type", ""),
                        "section_path": metadata.get("section_path", "").split(" > ")
                        if metadata.get("section_path")
                        else ["Document"],
                        "page_number": int(metadata.get("page_number", 1)),
                        "token_count": int(metadata.get("token_count", len(text_value.split()))),
                    },
                    "score": 1.0 / (1.0 + float(distance)),
                }
            )
        return rows


def available_vector_store_backends() -> list[VectorStoreBackend]:
    backends: list[VectorStoreBackend] = []
    try:
        import chromadb  # noqa: F401

        backends.append(VectorStoreBackend.CHROMA)
    except ImportError:
        pass
    backends.append(VectorStoreBackend.JSONL)
    return backends


def get_vector_store(
    store_path: Path,
    *,
    embedder: object,
    backend: VectorStoreBackend | None = None,
) -> ChromaVectorStore | VectorStore:
    selected = backend or available_vector_store_backends()[0]
    if selected == VectorStoreBackend.CHROMA:
        try:
            chroma_dir = store_path if store_path.suffix == "" else store_path.parent
            raw_name = store_path.stem if store_path.suffix else store_path.name
            collection_name = "".join(
                character if character.isalnum() or character in {"_", "-"} else "_"
                for character in raw_name
            ) or "quoteguard_chunks"
            return ChromaVectorStore(chroma_dir, embedder=embedder, collection_name=collection_name)
        except ImportError:
            return VectorStore(store_path=store_path, embedder=embedder)  # type: ignore[arg-type]
    return VectorStore(store_path=store_path, embedder=embedder)  # type: ignore[arg-type]
