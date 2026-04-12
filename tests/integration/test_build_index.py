from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_index import build_index
from quoteguard.config.settings import settings
from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.parser import ParserBackend
from quoteguard.retrieval.vector_store import VectorStoreBackend


class BuildIndexTest(unittest.TestCase):
    def test_build_index_persists_parsed_docs_and_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            raw_dir.mkdir()
            (raw_dir / "sample.txt").write_text(
                "# Coverage\nThe policy covers theft after forcible entry.\n## Limits\nItem limits apply.",
                encoding="utf-8",
            )

            original_parsed_dir = settings.parsed_dir
            original_chunks_path = settings.chunks_path
            original_vector_store_dir = settings.vector_store_dir
            try:
                settings.parsed_dir = base / "parsed"
                settings.chunks_path = base / "chunks" / "chunks.jsonl"
                settings.vector_store_dir = base / "vectors"
                with contextlib.redirect_stdout(io.StringIO()):
                    build_index(
                        raw_dir=raw_dir,
                        parser_backend=ParserBackend.TEXT_FALLBACK,
                        embedder_backend=EmbedderBackend.HASHING,
                        vector_store_backend=VectorStoreBackend.JSONL,
                    )
                parsed_files = list(settings.parsed_dir.glob("*.json"))
                self.assertEqual(len(parsed_files), 1)
                rows = [
                    json.loads(line)
                    for line in settings.chunks_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertGreaterEqual(len(rows), 1)
            finally:
                settings.parsed_dir = original_parsed_dir
                settings.chunks_path = original_chunks_path
                settings.vector_store_dir = original_vector_store_dir


if __name__ == "__main__":
    unittest.main()
