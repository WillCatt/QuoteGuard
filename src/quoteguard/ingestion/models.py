"""Ingestion data models."""

from __future__ import annotations

from quoteguard._compat import BaseModel, Field, ValidationError


class DocumentSection(BaseModel):
    heading: str
    text: str
    page_number: int = 1
    section_path: list[str] = Field(default_factory=list)

    def __post_init_model__(self) -> None:
        if not self.text.strip():
            raise ValidationError("DocumentSection.text must not be empty")
        if not self.section_path:
            self.section_path = [self.heading]


class ParsedDocument(BaseModel):
    source_pdf: str
    product_type: str = "home_contents"
    parser_backend: str = "text_fallback"
    sections: list[DocumentSection] = Field(default_factory=list)

    def __post_init_model__(self) -> None:
        if not self.sections:
            raise ValidationError("ParsedDocument.sections must not be empty")


class Chunk(BaseModel):
    chunk_id: str
    text: str
    source_pdf: str
    product_type: str
    section_path: list[str]
    page_number: int
    token_count: int

    def __post_init_model__(self) -> None:
        if not self.text.strip():
            raise ValidationError("Chunk.text must not be empty")
        if self.token_count <= 0:
            raise ValidationError("Chunk.token_count must be positive")
