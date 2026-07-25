from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

from apmatia.core.registry import ModuleCategory, ModuleStatus


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    status: ModuleStatus = ModuleStatus.DEVELOPMENT
    category: ModuleCategory = ModuleCategory.FEATURE
    default_enabled: bool = True
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)

    @property
    def is_stable(self) -> bool:
        return self.status is ModuleStatus.STABLE

    @property
    def is_development(self) -> bool:
        return self.status is ModuleStatus.DEVELOPMENT

    @property
    def is_visible_by_default(self) -> bool:
        return self.is_stable and self.default_enabled


def load_module_manifest(module_dir: Path) -> ModuleManifest:
    manifest_path = module_dir / "manifest.toml"
    with manifest_path.open("rb") as handle:
        payload = tomllib.load(handle)

    module_data = payload.get("module", {}) if isinstance(payload, dict) else {}
    metadata_data = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    dependencies_data = payload.get("dependencies", {}) if isinstance(payload, dict) else {}
    if not isinstance(module_data, dict):
        module_data = {}
    if not isinstance(metadata_data, dict):
        metadata_data = {}
    if not isinstance(dependencies_data, dict):
        dependencies_data = {}

    extension_metadata = {
        key: value
        for key, value in module_data.items()
        if key not in {
            "module_id", "name", "version", "description", "author",
            "status", "category", "default_enabled", "tags",
        }
    }
    extension_metadata.update(metadata_data)

    status_value = _first_class_value(module_data, metadata_data, "status", ModuleStatus.DEVELOPMENT.value)
    category_value = _first_class_value(module_data, metadata_data, "category", ModuleCategory.FEATURE.value)
    tags_value = _first_class_value(module_data, metadata_data, "tags", [])
    default_enabled = module_data.get("default_enabled", True)
    for standard_key in ("status", "category", "tags", "default_enabled"):
        extension_metadata.pop(standard_key, None)

    return ModuleManifest(
        module_id=str(module_data.get("module_id", module_dir.name)),
        name=str(module_data.get("name", module_dir.name)),
        version=str(module_data.get("version", "0.1.0")),
        description=str(module_data.get("description", "")),
        author=str(module_data.get("author", "")),
        status=_parse_enum(status_value, ModuleStatus, "status"),
        category=_parse_enum(category_value, ModuleCategory, "category"),
        default_enabled=_parse_bool(default_enabled, "default_enabled"),
        tags=_parse_tags(tags_value),
        metadata=extension_metadata,
        dependencies=dict(dependencies_data),
    )


def _first_class_value(module_data: dict[str, Any], metadata_data: dict[str, Any], key: str, default: Any) -> Any:
    return module_data[key] if key in module_data else metadata_data.get(key, default)


def _parse_enum(value: Any, enum_type: type[ModuleStatus] | type[ModuleCategory], field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        supported = ", ".join(member.value for member in enum_type)
        raise ValueError(f"Unsupported module {field_name} {value!r}; expected one of: {supported}.") from exc


def _parse_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Module {field_name} must be a boolean, got {value!r}.")
    return value


def _parse_tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(tag, str) for tag in value):
        raise ValueError(f"Module tags must be a list of strings, got {value!r}.")
    return tuple(value)
