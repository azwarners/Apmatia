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


def load_module_manifest(module_dir: Path) -> ModuleManifest:
    manifest_path = module_dir / "manifest.toml"
    with manifest_path.open("rb") as handle:
        payload = tomllib.load(handle)

    module_data = payload.get("module", {}) if isinstance(payload, dict) else {}
    if not isinstance(module_data, dict):
        module_data = {}

    return ModuleManifest(
        module_id=str(module_data.get("module_id", module_dir.name)),
        name=str(module_data.get("name", module_dir.name)),
        version=str(module_data.get("version", "0.1.0")),
        description=str(module_data.get("description", "")),
        author=str(module_data.get("author", "")),
        metadata={key: value for key, value in module_data.items() if key not in {"module_id", "name", "version", "description", "author"}},
    )
