from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)


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

    module_metadata = {
        key: value
        for key, value in module_data.items()
        if key not in {"module_id", "name", "version", "description", "author"}
    }
    if module_metadata:
        module_metadata.update(metadata_data)
    else:
        module_metadata = dict(metadata_data)

    return ModuleManifest(
        module_id=str(module_data.get("module_id", module_dir.name)),
        name=str(module_data.get("name", module_dir.name)),
        version=str(module_data.get("version", "0.1.0")),
        description=str(module_data.get("description", "")),
        author=str(module_data.get("author", "")),
        metadata=module_metadata,
        dependencies=dict(dependencies_data),
    )
