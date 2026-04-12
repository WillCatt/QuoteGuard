"""LLM client wrapper with file-based prompt rendering and disk cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from string import Formatter
from typing import Any

from quoteguard._compat import BaseModel, ValidationError
from quoteguard.config.settings import settings
from quoteguard.llm.structured_output import validate_payload


class CachedResponse(BaseModel):
    model: str
    prompt: str
    temperature: float = 0.0
    response_text: str


class TemplateRenderer:
    def render(self, template_path: Path, **context: Any) -> str:
        template = template_path.read_text(encoding="utf-8")
        return Formatter().vformat(template, args=(), kwargs=context)


class LLMClient:
    def __init__(self, cache_dir: Path | None = None, renderer: TemplateRenderer | None = None):
        self.cache_dir = cache_dir or settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.renderer = renderer or TemplateRenderer()

    def _cache_path(self, prompt: str, model: str, temperature: float) -> Path:
        digest = hashlib.sha256(f"{model}|{temperature}|{prompt}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def render_prompt(self, template_path: Path, **context: Any) -> str:
        return self.renderer.render(template_path, **context)

    def complete(
        self,
        *,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        selected_model = model or settings.default_model
        cache_path = self._cache_path(prompt, selected_model, temperature)
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))["response_text"]
        # Fallback behavior for scaffolding: echo a deterministic safe response.
        response_text = json.dumps({"message": "stubbed_response", "prompt_preview": prompt[:120]})
        cache_path.write_text(
            json.dumps(
                CachedResponse(
                    model=selected_model,
                    prompt=prompt,
                    temperature=temperature,
                    response_text=response_text,
                ).model_dump()
            ),
            encoding="utf-8",
        )
        return response_text

    def complete_structured(
        self,
        *,
        prompt: str,
        model_type: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> BaseModel:
        errors: list[str] = []
        current_prompt = prompt
        for _ in range(max_retries + 1):
            response = self.complete(prompt=current_prompt, model=model, temperature=temperature)
            try:
                return validate_payload(response, model_type)
            except ValidationError as exc:
                errors.append(str(exc))
                current_prompt = (
                    f"{prompt}\n\nRepair instruction: return valid JSON for {model_type.__name__}. "
                    f"Previous error: {exc}"
                )
        raise ValidationError("; ".join(errors))
