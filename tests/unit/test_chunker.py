from __future__ import annotations

import unittest

from quoteguard.ingestion.chunker import HierarchicalChunker
from quoteguard.ingestion.models import DocumentSection, ParsedDocument


class ChunkerTest(unittest.TestCase):
    def test_chunker_respects_max_tokens(self) -> None:
        document = ParsedDocument(
            source_pdf="sample.pdf",
            sections=[
                DocumentSection(
                    heading="Coverage",
                    text=" ".join(["word"] * 24),
                    page_number=1,
                    section_path=["Coverage"],
                )
            ],
        )
        chunker = HierarchicalChunker(max_tokens=10, overlap_tokens=2)
        chunks = chunker.chunk_document(document)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.token_count <= 10 for chunk in chunks))
        self.assertTrue(all(chunk.section_path == ["Coverage"] for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
