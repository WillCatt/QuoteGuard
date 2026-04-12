from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from quoteguard.ingestion.parser import (
    ParserBackend,
    TextFallbackParser,
    _sectionize_markdown,
    get_parser,
    persist_parsed_document,
)


class ParserTest(unittest.TestCase):
    def test_sectionize_markdown_preserves_headings(self) -> None:
        sections = _sectionize_markdown("# Coverage\nTheft is covered.\n## Limits\nApply item limits.")
        self.assertEqual(sections[0].section_path, ["Coverage"])
        self.assertEqual(sections[1].section_path, ["Coverage", "Limits"])

    def test_missing_explicit_backend_falls_back_to_text_parser(self) -> None:
        parser = get_parser(ParserBackend.PYMUPDF4LLM)
        self.assertIsInstance(parser, TextFallbackParser)

    def test_persist_parsed_document_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "doc.txt"
            source.write_text("# Coverage\nTheft is covered.", encoding="utf-8")
            document = TextFallbackParser().parse(source)
            output = Path(tmp_dir) / "parsed.json"
            persist_parsed_document(document, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["source_pdf"], "doc.txt")
            self.assertEqual(payload["parser_backend"], "text_fallback")


if __name__ == "__main__":
    unittest.main()
