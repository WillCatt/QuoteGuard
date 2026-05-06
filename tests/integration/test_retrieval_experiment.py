from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from quoteguard.ingestion.embedder import EmbedderBackend
from quoteguard.ingestion.parser import ParserBackend
from quoteguard.observability.retrieval_lab import run_retrieval_experiment
from quoteguard.retrieval.vector_store import VectorStoreBackend


class RetrievalExperimentTest(unittest.TestCase):
    def test_run_retrieval_experiment_writes_expected_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            raw_dir = base / "raw"
            runs_root = base / "runs"
            questions_path = base / "questions.jsonl"
            raw_dir.mkdir()

            (raw_dir / "sample.txt").write_text(
                "# Coverage\nThe policy covers theft after forcible entry.\n## Limits\nItem limits apply.",
                encoding="utf-8",
            )
            questions_path.write_text(
                json.dumps(
                    {
                        "question_id": "q001",
                        "question": "Does the policy cover theft?",
                        "expected_answer": "The policy covers theft after forcible entry.",
                        "answerable": True,
                        "source_pdf": "sample.txt",
                        "supporting_pages": [1],
                        "supporting_section_heading": "Coverage",
                        "required_evidence_text": "The policy covers theft after forcible entry.",
                        "difficulty": "easy",
                        "category": "direct_lookup",
                        "ambiguity_notes": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            run_dir = run_retrieval_experiment(
                raw_dir=raw_dir,
                questions_path=questions_path,
                parser_backend=ParserBackend.TEXT_FALLBACK,
                chunking_method="hybrid_section_aware",
                chunk_size=200,
                overlap_ratio=0.1,
                embedder_backend=EmbedderBackend.HASHING,
                vector_store_backend=VectorStoreBackend.JSONL,
                run_id="test-run",
                runs_root=runs_root,
            )

            self.assertTrue((run_dir / "config.json").exists())
            self.assertTrue((run_dir / "metrics.json").exists())
            self.assertTrue((run_dir / "results.csv").exists())
            self.assertTrue((run_dir / "failures.md").exists())
            self.assertTrue((run_dir / "sample_retrievals.md").exists())
            self.assertTrue((run_dir / "chunks.jsonl").exists())
            self.assertTrue((run_dir / "parsed" / "sample.txt.json").exists())

            config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
            metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(config["run_id"], "test-run")
            self.assertEqual(config["chunking_method"], "hybrid_section_aware")
            self.assertEqual(metrics["chunking_summary"]["number_of_chunks"], 2)
            self.assertEqual(len(metrics["corpus_audit"]), 1)


if __name__ == "__main__":
    unittest.main()
