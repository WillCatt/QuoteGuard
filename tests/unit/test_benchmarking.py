from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.embedder import SentenceTransformerEmbedder
from quoteguard.ingestion.parser import ParserBackend
from quoteguard.observability.benchmarking import build_benchmark_report
from quoteguard.retrieval.vector_store import VectorStoreBackend


class BenchmarkingTest(unittest.TestCase):
    def test_build_benchmark_report_emits_run_summary_and_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            benchmark_dir = base / "benchmarks"
            raw_dir.mkdir()
            (raw_dir / "sample.txt").write_text(
                "# Coverage\nThe policy covers theft after forcible entry.\n## Limits\nItem limits apply.",
                encoding="utf-8",
            )

            report = build_benchmark_report(
                raw_dir,
                parser_backends=[ParserBackend.TEXT_FALLBACK],
                questions=["Does the policy cover theft?"],
                embedder_backends=[EmbedderBackend.HASHING],
                vector_store_backends=[VectorStoreBackend.JSONL],
                benchmark_dir=benchmark_dir,
            )

            self.assertEqual(report["product_type"], "home_contents")
            self.assertEqual(len(report["runs"]), 1)
            run = report["runs"][0]
            self.assertEqual(run["status"], "ok")
            self.assertEqual(run["summary"]["documents_parsed"], 1)
            self.assertGreater(run["summary"]["chunks_total"], 0)
            self.assertEqual(len(run["queries"]), 1)
            self.assertEqual(run["queries"][0]["question"], "Does the policy cover theft?")

    def test_build_benchmark_report_supports_multiple_backend_combinations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            benchmark_dir = base / "benchmarks"
            raw_dir.mkdir()
            (raw_dir / "sample.txt").write_text(
                "# Coverage\nThe policy covers theft after forcible entry.\n## Limits\nItem limits apply.",
                encoding="utf-8",
            )

            with patch.object(SentenceTransformerEmbedder, "__init__", side_effect=RuntimeError):
                report = build_benchmark_report(
                    raw_dir,
                    parser_backends=[ParserBackend.TEXT_FALLBACK],
                    questions=["Does the policy cover theft?"],
                    embedder_backends=[EmbedderBackend.HASHING, EmbedderBackend.SENTENCE_TRANSFORMERS],
                    vector_store_backends=[VectorStoreBackend.JSONL, VectorStoreBackend.CHROMA],
                    benchmark_dir=benchmark_dir,
                )

            self.assertEqual(report["embedder_backends"], ["hashing", "sentence_transformers"])
            self.assertEqual(report["vector_store_backends"], ["jsonl", "chroma"])
            self.assertEqual(len(report["runs"]), 4)


if __name__ == "__main__":
    unittest.main()
