"""Project settings."""

from __future__ import annotations

import os
from pathlib import Path

from quoteguard._compat import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    environment: str = Field(default="development")
    data_dir: Path = Field(default=ROOT_DIR / "data")
    log_dir: Path = Field(default=ROOT_DIR / "data" / "processed" / "logs")
    cache_dir: Path = Field(default=ROOT_DIR / "data" / "processed" / "cache")
    vector_store_dir: Path = Field(default=ROOT_DIR / "data" / "processed" / "chroma")
    parsed_dir: Path = Field(default=ROOT_DIR / "data" / "processed" / "parsed")
    chunks_path: Path = Field(default=ROOT_DIR / "data" / "processed" / "chunks" / "chunks.jsonl")
    audit_log_path: Path = Field(default=ROOT_DIR / "data" / "processed" / "logs" / "audit.jsonl")
    default_model: str = Field(default="llama3.1:8b-instruct-q4_K_M")
    json_model: str = Field(default="qwen2.5:7b-instruct")
    embed_model: str = Field(default="BAAI/bge-small-en-v1.5")
    product_type: str = Field(default="home_contents")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("QUOTEGUARD_ENV", "development"),
            data_dir=Path(os.getenv("QUOTEGUARD_DATA_DIR", ROOT_DIR / "data")),
            log_dir=Path(os.getenv("QUOTEGUARD_LOG_DIR", ROOT_DIR / "data" / "processed" / "logs")),
            cache_dir=Path(
                os.getenv("QUOTEGUARD_CACHE_DIR", ROOT_DIR / "data" / "processed" / "cache")
            ),
            vector_store_dir=Path(
                os.getenv("QUOTEGUARD_VECTOR_STORE_DIR", ROOT_DIR / "data" / "processed" / "chroma")
            ),
            parsed_dir=Path(
                os.getenv("QUOTEGUARD_PARSED_DIR", ROOT_DIR / "data" / "processed" / "parsed")
            ),
            chunks_path=Path(
                os.getenv(
                    "QUOTEGUARD_CHUNKS_PATH",
                    ROOT_DIR / "data" / "processed" / "chunks" / "chunks.jsonl",
                )
            ),
            audit_log_path=Path(
                os.getenv(
                    "QUOTEGUARD_AUDIT_LOG_PATH",
                    ROOT_DIR / "data" / "processed" / "logs" / "audit.jsonl",
                )
            ),
            default_model=os.getenv("QUOTEGUARD_DEFAULT_MODEL", "llama3.1:8b-instruct-q4_K_M"),
            json_model=os.getenv("QUOTEGUARD_JSON_MODEL", "qwen2.5:7b-instruct"),
            embed_model=os.getenv("QUOTEGUARD_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
            product_type=os.getenv("QUOTEGUARD_PRODUCT_TYPE", "home_contents"),
        )

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.log_dir, self.cache_dir, self.vector_store_dir, self.parsed_dir):
            path.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings.from_env()
