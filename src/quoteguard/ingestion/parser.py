"""PDF parsing abstraction with optional backends."""

from __future__ import annotations

from enum import Enum
import json
from pathlib import Path
from typing import Protocol

from quoteguard.ingestion.models import DocumentSection, ParsedDocument


class ParserBackend(str, Enum):
    PYMUPDF4LLM = "pymupdf4llm"
    DOCLING = "docling"
    TEXT_FALLBACK = "text_fallback"


class Parser(Protocol):
    def parse(self, pdf_path: Path, product_type: str = "home_contents") -> ParsedDocument: ...


def _sectionize_markdown(markdown_text: str, *, page_number: int = 1) -> list[DocumentSection]:
    sections: list[DocumentSection] = []
    current_heading = "Document"
    current_path = [current_heading]
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if not text:
            return
        sections.append(
            DocumentSection(
                heading=current_heading,
                text=text,
                page_number=page_number,
                section_path=list(current_path),
            )
        )
        buffer.clear()

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip() or "Untitled"
            if level <= 1:
                current_path = [heading]
            else:
                current_path = current_path[: max(0, level - 1)] + [heading]
            current_heading = heading
            continue
        buffer.append(line)
    flush()
    return sections or [
        DocumentSection(
            heading="Document",
            text=markdown_text.strip() or "No text extracted",
            page_number=page_number,
            section_path=["Document"],
        )
    ]


def persist_parsed_document(document: ParsedDocument, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )


class TextFallbackParser:
    """Fallback parser used when PDF-specific libraries are unavailable."""

    def parse(self, pdf_path: Path, product_type: str = "home_contents") -> ParsedDocument:
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        content = pdf_path.read_text(encoding="utf-8", errors="ignore")
        sections = _sectionize_markdown(content, page_number=1)
        return ParsedDocument(
            source_pdf=pdf_path.name,
            product_type=product_type,
            parser_backend=ParserBackend.TEXT_FALLBACK.value,
            sections=sections,
        )


class PyMuPDF4LLMParser:
    """PyMuPDF4LLM-backed parser when installed."""

    def __init__(self) -> None:
        import pymupdf4llm  # noqa: F401

    def parse(self, pdf_path: Path, product_type: str = "home_contents") -> ParsedDocument:
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        import pymupdf4llm

        page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        sections: list[DocumentSection] = []
        if isinstance(page_chunks, list):
            for index, page in enumerate(page_chunks, start=1):
                text = page.get("text", "")
                metadata = page.get("metadata", {})
                page_number = metadata.get("page") or metadata.get("page_number") or index
                sections.extend(_sectionize_markdown(text, page_number=int(page_number)))
        else:
            markdown_text = page_chunks if isinstance(page_chunks, str) else str(page_chunks)
            sections = _sectionize_markdown(markdown_text, page_number=1)
        return ParsedDocument(
            source_pdf=pdf_path.name,
            product_type=product_type,
            parser_backend=ParserBackend.PYMUPDF4LLM.value,
            sections=sections,
        )


class DoclingParser:
    """Docling-backed parser when installed."""

    def __init__(self) -> None:
        from docling.document_converter import DocumentConverter  # noqa: F401

    def parse(self, pdf_path: Path, product_type: str = "home_contents") -> ParsedDocument:
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        markdown_text = result.document.export_to_markdown()
        sections = _sectionize_markdown(markdown_text, page_number=1)
        return ParsedDocument(
            source_pdf=pdf_path.name,
            product_type=product_type,
            parser_backend=ParserBackend.DOCLING.value,
            sections=sections,
        )


def available_backends() -> list[ParserBackend]:
    backends: list[ParserBackend] = []
    try:
        import pymupdf4llm  # noqa: F401

        backends.append(ParserBackend.PYMUPDF4LLM)
    except ImportError:
        pass
    try:
        from docling.document_converter import DocumentConverter  # noqa: F401

        backends.append(ParserBackend.DOCLING)
    except ImportError:
        pass
    backends.append(ParserBackend.TEXT_FALLBACK)
    return backends


def parse_directory(
    source_dir: Path,
    *,
    backend: ParserBackend | None = None,
    product_type: str = "home_contents",
) -> list[ParsedDocument]:
    parser = get_parser(backend=backend)
    documents: list[ParsedDocument] = []
    for path in sorted(source_dir.iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        documents.append(parser.parse(path, product_type=product_type))
    return documents


def get_parser(backend: ParserBackend | None = None) -> Parser:
    selected = backend
    if selected is None:
        installed_backends = available_backends()
        selected = installed_backends[0]
    if selected == ParserBackend.PYMUPDF4LLM:
        try:
            return PyMuPDF4LLMParser()
        except ImportError:
            return TextFallbackParser()
    if selected == ParserBackend.DOCLING:
        try:
            return DoclingParser()
        except ImportError:
            return TextFallbackParser()
    return TextFallbackParser()
