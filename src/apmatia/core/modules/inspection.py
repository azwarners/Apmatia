from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apmatia.core.registry import get_application_registry

from .manifest import ModuleManifest, load_module_manifest
from .workspace import resolve_module_bundle_root, resolve_module_workspace_root


@dataclass(frozen=True, slots=True)
class ModuleInspection:
    manifest: ModuleManifest
    module_dir: Path
    source: str = "bundled"
    actions: tuple[str, ...] = field(default_factory=tuple)
    tools: tuple[str, ...] = field(default_factory=tuple)
    commands: tuple[str, ...] = field(default_factory=tuple)
    views: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": {
                "module_id": self.manifest.module_id,
                "name": self.manifest.name,
                "version": self.manifest.version,
                "description": self.manifest.description,
                "author": self.manifest.author,
                "metadata": dict(self.manifest.metadata),
                "dependencies": dict(self.manifest.dependencies),
            },
            "source": self.source,
            "is_workspace": self.source == "workspace",
            "actions": list(self.actions),
            "tools": list(self.tools),
            "commands": list(self.commands),
            "views": list(self.views),
        }


def list_bundled_module_inspections(base_dir: Path | None = None) -> list[ModuleInspection]:
    return _list_module_inspections(_modules_dir(base_dir), source="bundled", registry=get_application_registry())


def get_bundled_module_inspection(module_slug: str, base_dir: Path | None = None) -> ModuleInspection | None:
    for inspection in list_bundled_module_inspections(base_dir=base_dir):
        if inspection.manifest.module_id == module_slug:
            return inspection
    return None


def list_workspace_module_inspections(base_dir: Path | None = None) -> list[ModuleInspection]:
    return _list_module_inspections(_workspace_modules_dir(base_dir), source="workspace", registry=None)


def get_workspace_module_inspection(module_slug: str, base_dir: Path | None = None) -> ModuleInspection | None:
    for inspection in list_workspace_module_inspections(base_dir=base_dir):
        if inspection.manifest.module_id == module_slug:
            return inspection
    return None


def serialize_module_inspections(inspections: list[ModuleInspection]) -> list[dict[str, Any]]:
    return [inspection.to_dict() for inspection in inspections]


def serialize_module_inspection(inspection: ModuleInspection) -> dict[str, Any]:
    return inspection.to_dict()


def _modules_dir(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        bundled_path = base_dir / "src" / "apmatia" / "modules"
        if bundled_path.exists():
            return bundled_path
        legacy_path = base_dir / "src" / "modules"
        if legacy_path.exists():
            return legacy_path
        return bundled_path

    package = importlib.import_module("apmatia.modules")
    return Path(package.__path__[0])


def _workspace_modules_dir(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "workspace" / "modules"
    return resolve_module_workspace_root()


def _list_module_inspections(
    modules_dir: Path,
    *,
    source: str,
    registry: Any | None,
) -> list[ModuleInspection]:
    if not modules_dir.exists():
        return []

    inspections: list[ModuleInspection] = []
    actions = registry.list_actions() if registry is not None else []
    tools = registry.list_tools() if registry is not None else []
    commands = registry.list_commands() if registry is not None else []
    views = registry.list_views() if registry is not None else []

    for module_dir in sorted(path for path in modules_dir.iterdir() if path.is_dir()):
        manifest_path = module_dir / "manifest.toml"
        if not manifest_path.exists():
            continue
        manifest = load_module_manifest(module_dir)
        inspections.append(
            ModuleInspection(
                manifest=manifest,
                module_dir=module_dir,
                source=source,
                actions=_ids_for_module(actions, manifest.module_id, "action_id"),
                tools=_ids_for_module(tools, manifest.module_id, "tool_id"),
                commands=_ids_for_module(commands, manifest.module_id, "command_id"),
                views=_ids_for_module(views, manifest.module_id, "view_id"),
            )
        )
    return inspections


def _ids_for_module(items: list[Any], module_id: str, attribute_name: str) -> tuple[str, ...]:
    values = []
    for item in items:
        if getattr(item, "module_id", None) != module_id:
            continue
        value = getattr(item, attribute_name, "")
        if value:
            values.append(str(value))
    return tuple(values)
