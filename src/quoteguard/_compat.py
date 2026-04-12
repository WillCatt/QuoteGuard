"""Compatibility helpers when optional third-party dependencies are unavailable."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class ValidationError(ValueError):
    """Lightweight stand-in for pydantic validation errors."""


class FieldInfo:
    def __init__(self, default: Any = ..., default_factory: Any | None = None, description: str = ""):
        self.default = default
        self.default_factory = default_factory
        self.description = description


def Field(
    default: Any = ...,
    *,
    default_factory: Any | None = None,
    description: str = "",
) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory, description=description)


def _clone_default(value: Any) -> Any:
    if isinstance(value, (dict, list, set)):
        return deepcopy(value)
    return value


try:
    from pydantic import BaseModel, ConfigDict, Field as PydanticField, ValidationError as PydanticValidationError

    Field = PydanticField
    ValidationError = PydanticValidationError
except ImportError:
    class ConfigDict(dict):
        """Stub for pydantic's ConfigDict."""

    class BaseModel:
        """Minimal model API used by this repository."""

        model_config = ConfigDict()

        def __init__(self, **kwargs: Any):
            annotations = self.__class__.__dict__.get("__annotations__", {})
            for name in annotations:
                default = getattr(self.__class__, name, ...)
                if isinstance(default, FieldInfo):
                    if name in kwargs:
                        value = kwargs.pop(name)
                    elif default.default_factory is not None:
                        value = default.default_factory()
                    elif default.default is not ...:
                        value = _clone_default(default.default)
                    else:
                        raise ValidationError(f"Missing required field: {name}")
                elif name in kwargs:
                    value = kwargs.pop(name)
                elif default is not ...:
                    value = _clone_default(default)
                else:
                    raise ValidationError(f"Missing required field: {name}")
                setattr(self, name, value)
            for key, value in kwargs.items():
                setattr(self, key, value)
            validator = getattr(self, "__post_init_model__", None)
            if callable(validator):
                validator()

        @classmethod
        def model_validate(cls, data: Any) -> "BaseModel":
            if isinstance(data, cls):
                return data
            if not isinstance(data, dict):
                raise ValidationError(f"Expected mapping for {cls.__name__}")
            return cls(**data)

        def model_dump(self, *, exclude_none: bool = False) -> dict[str, Any]:
            data: dict[str, Any] = {}
            annotations = self.__class__.__dict__.get("__annotations__", {})
            for name in annotations:
                value = getattr(self, name)
                if exclude_none and value is None:
                    continue
                if isinstance(value, BaseModel):
                    data[name] = value.model_dump(exclude_none=exclude_none)
                elif isinstance(value, list):
                    items = []
                    for item in value:
                        if isinstance(item, BaseModel):
                            items.append(item.model_dump(exclude_none=exclude_none))
                        else:
                            items.append(item)
                    data[name] = items
                else:
                    data[name] = value
            return data

        def model_copy(self, *, update: dict[str, Any] | None = None) -> "BaseModel":
            payload = self.model_dump()
            if update:
                payload.update(update)
            return self.__class__.model_validate(payload)
