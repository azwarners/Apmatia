from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from datetime import date, datetime
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin


def build_collection_view_schema(
    model_type: type[Any],
    *,
    list_fields: tuple[str, ...] = (),
    create_fields: tuple[str, ...] = (),
    edit_fields: tuple[str, ...] = (),
    field_overrides: dict[str, dict[str, Any]] | None = None,
    create: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not is_dataclass(model_type):
        raise ValueError("Collection view schema inference requires a dataclass model type.")

    overrides = field_overrides or {}
    resolved_fields: list[dict[str, Any]] = []
    for dataclass_field in fields(model_type):
        override = dict(overrides.get(dataclass_field.name, {}))
        if override.get("hidden", False):
            continue

        field_schema = {
            "key": dataclass_field.name,
            "label": str(override.pop("label", _humanize(dataclass_field.name))),
            "data_type": str(override.pop("data_type", _infer_data_type(dataclass_field.type))),
            "field_type": str(override.pop("field_type", _infer_field_type(dataclass_field.type))),
            "create": bool(override.pop("create", dataclass_field.name in create_fields)),
            "edit": bool(override.pop("edit", dataclass_field.name in edit_fields or dataclass_field.name not in {"id", "created_at", "updated_at"})),
            "list": bool(override.pop("list", dataclass_field.name in list_fields)),
            "required": bool(override.pop("required", _is_required(dataclass_field))),
        }

        default = override.pop("default", _field_default(dataclass_field))
        if default is not None:
            field_schema["default"] = default

        for key in (
            "help_text",
            "placeholder",
            "empty_value",
            "min_value",
            "max_value",
            "step",
            "options",
        ):
            if key in override:
                field_schema[key] = override.pop(key)

        field_schema.update(override)
        resolved_fields.append(field_schema)

    return {
        "version": 1,
        "fields": resolved_fields,
        "create": dict(create or {}),
    }


def _field_default(dataclass_field) -> Any:
    if dataclass_field.default is not MISSING:
        return _json_safe_default(dataclass_field.default)
    if dataclass_field.default_factory is not MISSING:  # type: ignore[attr-defined]
        return _json_safe_default(dataclass_field.default_factory())  # type: ignore[misc]
    return None


def _json_safe_default(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return list(value)
    return None


def _is_required(dataclass_field) -> bool:
    if dataclass_field.default is not MISSING:
        return False
    if dataclass_field.default_factory is not MISSING:  # type: ignore[attr-defined]
        return False
    return not _is_optional(dataclass_field.type)


def _infer_data_type(annotation: Any) -> str:
    resolved = _unwrap_optional(annotation)
    origin = get_origin(resolved)
    if origin in {list, tuple}:
        args = get_args(resolved)
        if args and args[0] is str:
            return "string_list"
        return "list"
    if resolved is bool:
        return "boolean"
    if resolved in {int, float}:
        return "number"
    if resolved is date:
        return "date"
    if resolved is datetime:
        return "datetime"
    return "string"


def _infer_field_type(annotation: Any) -> str:
    data_type = _infer_data_type(annotation)
    if data_type == "boolean":
        return "checkbox"
    if data_type == "number":
        return "number"
    return "text"


def _unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin in {UnionType, Union}:
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(args) == 1:
            return args[0]
    return annotation


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin in {UnionType, Union}:
        return any(arg is NoneType for arg in get_args(annotation))
    return False


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()
