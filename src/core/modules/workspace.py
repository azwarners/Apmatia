from __future__ import annotations

from pathlib import Path


def resolve_module_bundle_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "src" / "modules"
    return Path.cwd() / "src" / "modules"


def resolve_module_workspace_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "workspace" / "modules"
    return Path.cwd() / "workspace" / "modules"


def resolve_module_target_root(*, workspace: bool = False, base_dir: Path | None = None) -> Path:
    return resolve_module_workspace_root(base_dir) if workspace else resolve_module_bundle_root(base_dir)


def resolve_module_target_dir(module_slug: str, *, workspace: bool = False, base_dir: Path | None = None) -> Path:
    return resolve_module_target_root(workspace=workspace, base_dir=base_dir) / module_slug
