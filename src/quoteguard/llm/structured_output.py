"""Structured output utilities."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from quoteguard._compat import BaseModel, ValidationError


ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_json_object(payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("Structured output must be a JSON object")
    return data


def validate_payload(payload: str | dict[str, Any], model_type: type[ModelT]) -> ModelT:
    data = parse_json_object(payload) if isinstance(payload, str) else payload
    return model_type.model_validate(data)
