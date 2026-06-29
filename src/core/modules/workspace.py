from __future__ import annotations

import os
from pathlib import Path

from src.core.app_config import get_config_value


def resolve_module_bundle_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "src" / "modules"
    return Path.cwd() / "src" / "modules"


def resolve_module_workspace_root(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir / "workspace" / "modules"

    env_override = os.getenv("APMATIA_WORKSPACE_ROOT")
    if env_override:
        return Path(env_override).expanduser()

    config_override = get_config_value("workspace", "root", default=None)
    if config_override:
        return Path(config_override).expanduser()

    return Path.home() / ".apmatia" / "workspace" / "modules"


class WorkspaceRootError(ValueError):
    pass


class WorkspaceRootNotFoundError(WorkspaceRootError):
    pass


class WorkspaceRootPermissionError(WorkspaceRootError):
    pass


def ensure_module_workspace_root(base_dir: Path | None = None) -> Path:
    root = resolve_module_workspace_root(base_dir)
    if not root.exists():
        raise WorkspaceRootNotFoundError(f"Workspace directory does not exist: {root}")
    if not os.access(root, os.W_OK):
        raise WorkspaceRootPermissionError(f"No write access to: {root}")
    return root


def resolve_module_target_root(*, workspace: bool = False, base_dir: Path | None = None) -> Path:
    return resolve_module_workspace_root(base_dir) if workspace else resolve_module_bundle_root(base_dir)


def resolve_module_target_dir(module_slug: str, *, workspace: bool = False, base_dir: Path | None = None) -> Path:
    return resolve_module_target_root(workspace=workspace, base_dir=base_dir) / module_slug
