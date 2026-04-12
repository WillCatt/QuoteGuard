"""Chunking logic preserving section metadata."""

from __future__ import annotations

from collections.abc import Iterable

from quoteguard.ingestion.models import Chunk, ParsedDocument


def token_count(text: str) -> int:
    return len(text.split())


class HierarchicalChunker:
    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section_index, section in enumerate(document.sections):
            words = section.text.split()
            if len(words) <= self.max_tokens:
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.source_pdf}:{section_index}:0",
                        text=section.text,
                        source_pdf=document.source_pdf,
                        product_type=document.product_type,
                        section_path=section.section_path,
                        page_number=section.page_number,
                        token_count=token_count(section.text),
                    )
                )
                continue
            step = max(1, self.max_tokens - self.overlap_tokens)
            window_index = 0
            for start in range(0, len(words), step):
                window = words[start : start + self.max_tokens]
                if not window:
                    break
                text = " ".join(window)
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.source_pdf}:{section_index}:{window_index}",
                        text=text,
                        source_pdf=document.source_pdf,
                        product_type=document.product_type,
                        section_path=section.section_path,
                        page_number=section.page_number,
                        token_count=len(window),
                    )
                )
                window_index += 1
                if start + self.max_tokens >= len(words):
                    break
        return chunks

    def chunk_documents(self, documents: Iterable[ParsedDocument]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self.chunk_document(document))
        return chunks
