from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apmatia.core.app_config import get_config_value
from apmatia.core.runtime_paths import get_app_dir

_WORKSPACE_KIND_DIRS = {
    "agent": "agents",
    "group": "groups",
    "project": "projects",
}


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path

    @property
    def agents(self) -> Path:
        return self.root / _WORKSPACE_KIND_DIRS["agent"]

    @property
    def groups(self) -> Path:
        return self.root / _WORKSPACE_KIND_DIRS["group"]

    @property
    def projects(self) -> Path:
        return self.root / _WORKSPACE_KIND_DIRS["project"]

    def kind_root(self, kind: str) -> Path:
        normalized_kind = _normalize_workspace_kind(kind)
        return self.root / _WORKSPACE_KIND_DIRS[normalized_kind]

    def agent_root(self, agent: Any, base_dir: Path | None = None) -> Path:
        return _resolve_record_workspace_root_on_root("agent", agent, workspace_root=base_dir or self.root)

    def group_root(self, group: Any, base_dir: Path | None = None) -> Path:
        return _resolve_record_workspace_root_on_root("group", group, workspace_root=base_dir or self.root)

    def project_root(self, project: Any, base_dir: Path | None = None) -> Path:
        return _resolve_record_workspace_root_on_root("project", project, workspace_root=base_dir or self.root)


def resolve_workspace_root(base_dir: Path | None = None) -> Path:
    env_override = os.getenv("APMATIA_WORKSPACE_ROOT")
    if env_override:
        return Path(env_override).expanduser()

    config_override = get_config_value("workspace", "root", default=None)
    if config_override:
        return Path(config_override).expanduser()

    if base_dir is not None:
        return Path(base_dir).expanduser().resolve() / "workspace"

    return get_app_dir() / "workspace"


def get_workspace(base_dir: Path | None = None) -> Workspace:
    return Workspace(root=resolve_workspace_root(base_dir))


def resolve_workspace_kind_root(kind: str, base_dir: Path | None = None) -> Path:
    normalized_kind = _normalize_workspace_kind(kind)
    return resolve_workspace_root(base_dir) / _WORKSPACE_KIND_DIRS[normalized_kind]


def resolve_agent_workspace_root(agent: Any, base_dir: Path | None = None) -> Path:
    return _resolve_record_workspace_root("agent", agent, base_dir=base_dir)


def resolve_group_workspace_root(group: Any, base_dir: Path | None = None) -> Path:
    return _resolve_record_workspace_root("group", group, base_dir=base_dir)


def resolve_project_workspace_root(project: Any, base_dir: Path | None = None) -> Path:
    return _resolve_record_workspace_root("project", project, base_dir=base_dir)


def _resolve_record_workspace_root(kind: str, record: Any, *, base_dir: Path | None = None) -> Path:
    explicit_root = str(getattr(record, "workspace_root", "") or "").strip()
    if explicit_root:
        return Path(explicit_root).expanduser()

    record_id = getattr(record, "id", None)
    if record_id is None:
        raise ValueError(f"{kind.title()} workspace root cannot be resolved before the record has an id.")

    return resolve_workspace_kind_root(kind, base_dir=base_dir) / f"{kind}-{_workspace_segment(record_id)}"


def _resolve_record_workspace_root_on_root(kind: str, record: Any, *, workspace_root: Path) -> Path:
    explicit_root = str(getattr(record, "workspace_root", "") or "").strip()
    if explicit_root:
        return Path(explicit_root).expanduser()

    record_id = getattr(record, "id", None)
    if record_id is None:
        raise ValueError(f"{kind.title()} workspace root cannot be resolved before the record has an id.")

    normalized_kind = _normalize_workspace_kind(kind)
    return workspace_root / _WORKSPACE_KIND_DIRS[normalized_kind] / f"{kind}-{_workspace_segment(record_id)}"


def _normalize_workspace_kind(kind: str) -> str:
    normalized = str(kind or "").strip().lower()
    if normalized not in _WORKSPACE_KIND_DIRS:
        raise ValueError(f"Unsupported workspace kind: {kind}")
    return normalized


def _workspace_segment(value: object) -> str:
    segment = str(value or "").strip()
    if not segment:
        raise ValueError("Workspace identifier cannot be empty.")
    if segment in {".", ".."} or "/" in segment or "\\" in segment:
        raise ValueError(f"Workspace identifier is not safe to use in a path: {segment}")
    return segment
