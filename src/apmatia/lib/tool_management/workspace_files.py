from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apmatia.core.runtime_paths import get_app_dir
from apmatia.core.modules import (
    WorkspaceFileNotFoundError,
    WorkspacePathError,
    WorkspaceRootError,
    WorkspaceRootNotFoundError,
    WorkspaceRootPermissionError,
)
from apmatia.core.workspaces import resolve_agent_workspace_root
from apmatia.lib.agent_management.services import AgentService
from apmatia.lib.tool_management.registry import ToolProvider


WORKSPACE_FILE_PROVIDER_IDS = {
    "list": "builtin.workspace_list_files",
    "read": "builtin.workspace_read_file",
    "write": "builtin.workspace_write_file",
    "delete": "builtin.workspace_delete_file",
}


def workspace_file_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "workspace_list_files",
            "description": "List files in the calling agent's workspace root.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": WORKSPACE_FILE_PROVIDER_IDS["list"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "workspace_files", "workspace": True, "tool": "list_files"},
        },
        {
            "name": "workspace_read_file",
            "description": "Read a UTF-8 file from the calling agent's workspace root.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                },
                "required": ["relative_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": WORKSPACE_FILE_PROVIDER_IDS["read"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True, "library": "workspace_files", "workspace": True, "tool": "read_file"},
        },
        {
            "name": "workspace_write_file",
            "description": "Write a UTF-8 file inside the calling agent's workspace root.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["relative_path", "content"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": WORKSPACE_FILE_PROVIDER_IDS["write"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "library": "workspace_files", "workspace": True, "tool": "write_file"},
        },
        {
            "name": "workspace_delete_file",
            "description": "Delete a file inside the calling agent's workspace root.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                },
                "required": ["relative_path"],
                "additionalProperties": False,
            },
            "output_schema": {"type": "object"},
            "provider_id": WORKSPACE_FILE_PROVIDER_IDS["delete"],
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True, "library": "workspace_files", "workspace": True, "tool": "delete_file"},
        },
    ]


@dataclass(slots=True)
class WorkspaceFileEntry:
    relative_path: str
    path: Path
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
        }


@dataclass(slots=True)
class WorkspaceFileContent:
    agent_id: int
    workspace_root: Path
    relative_path: str
    path: Path
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "workspace_root": str(self.workspace_root),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "content": self.content,
        }


@dataclass(slots=True)
class WorkspaceFileWriteResult:
    agent_id: int
    workspace_root: Path
    relative_path: str
    path: Path
    created: bool
    bytes_written: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "workspace_root": str(self.workspace_root),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "created": self.created,
            "bytes_written": self.bytes_written,
        }


@dataclass(slots=True)
class WorkspaceFileDeleteResult:
    agent_id: int
    workspace_root: Path
    relative_path: str
    path: Path
    deleted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "workspace_root": str(self.workspace_root),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "deleted": self.deleted,
        }


@dataclass(slots=True)
class WorkspaceFileToolProvider:
    provider_id: str
    action: str
    agent_service: AgentService
    base_dir: Path | None = None

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if tool_call is None:
            raise ValueError("Tool call context is required.")

        agent = self.agent_service.get_agent(int(tool_call.requester_agent_id))
        if agent is None or agent.id is None:
            raise ValueError(f"Calling agent is unavailable: {tool_call.requester_agent_id}")

        workspace_root = _resolve_agent_workspace_root(agent, base_dir=self.base_dir)
        if self.action == "list":
            root = _ensure_workspace_root(workspace_root)
            files = _list_workspace_files(root)
            return {
                "agent_id": int(agent.id),
                "workspace_root": str(root),
                "count": len(files),
                "files": [file.to_dict() for file in files],
            }

        if self.action == "read":
            root = _ensure_workspace_root(workspace_root)
            result = _read_workspace_file(root, str(arguments["relative_path"]), agent_id=int(agent.id))
            return result.to_dict()

        if self.action == "write":
            root = _prepare_workspace_root_for_write(workspace_root)
            result = _write_workspace_file(
                root,
                str(arguments["relative_path"]),
                str(arguments.get("content") or ""),
                agent_id=int(agent.id),
            )
            return result.to_dict()

        if self.action == "delete":
            root = _ensure_workspace_root(workspace_root)
            result = _delete_workspace_file(root, str(arguments["relative_path"]), agent_id=int(agent.id))
            return result.to_dict()

        raise ValueError(f"Unsupported workspace file tool action: {self.action}")


def build_workspace_file_tool_providers(
    agent_service: AgentService,
    base_dir: Path | None = None,
) -> list[WorkspaceFileToolProvider]:
    return [
        WorkspaceFileToolProvider(WORKSPACE_FILE_PROVIDER_IDS["list"], "list", agent_service=agent_service, base_dir=base_dir),
        WorkspaceFileToolProvider(WORKSPACE_FILE_PROVIDER_IDS["read"], "read", agent_service=agent_service, base_dir=base_dir),
        WorkspaceFileToolProvider(WORKSPACE_FILE_PROVIDER_IDS["write"], "write", agent_service=agent_service, base_dir=base_dir),
        WorkspaceFileToolProvider(WORKSPACE_FILE_PROVIDER_IDS["delete"], "delete", agent_service=agent_service, base_dir=base_dir),
    ]


def _resolve_agent_workspace_root(agent: Any, *, base_dir: Path | None) -> Path:
    return resolve_agent_workspace_root(agent, base_dir=base_dir)


def _ensure_workspace_root(root: Path) -> Path:
    if not root.exists():
        if _is_within_app_workspace_root(root):
            root.mkdir(parents=True, exist_ok=True)
        else:
            raise WorkspaceRootNotFoundError(f"Workspace root does not exist: {root}")
    if not root.is_dir():
        raise WorkspaceRootError(f"Workspace root is not a directory: {root}")
    if not os.access(root, os.R_OK | os.X_OK):
        raise WorkspaceRootPermissionError(f"No read access to workspace root: {root}")
    return root


def _prepare_workspace_root_for_write(root: Path) -> Path:
    if root.exists() and not root.is_dir():
        raise WorkspaceRootError(f"Workspace root is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    if not os.access(root, os.W_OK | os.X_OK):
        raise WorkspaceRootPermissionError(f"No write access to workspace root: {root}")
    return root


def _is_within_app_workspace_root(path: Path) -> bool:
    app_workspace_root = (get_app_dir() / "workspace").expanduser().resolve(strict=False)
    resolved_path = path.expanduser().resolve(strict=False)
    return resolved_path == app_workspace_root or app_workspace_root in resolved_path.parents


def _list_workspace_files(root: Path) -> list[WorkspaceFileEntry]:
    files: list[WorkspaceFileEntry] = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: str(item.relative_to(root))):
        resolved = path.resolve(strict=True)
        _ensure_within_root(resolved, root)
        files.append(
            WorkspaceFileEntry(
                relative_path=str(resolved.relative_to(root)),
                path=resolved,
                size_bytes=resolved.stat().st_size,
            )
        )
    return files


def _read_workspace_file(root: Path, relative_path: str, *, agent_id: int) -> WorkspaceFileContent:
    path = _resolve_workspace_file_path(root, relative_path)
    if not path.exists() or not path.is_file():
        raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")
    return WorkspaceFileContent(
        agent_id=agent_id,
        workspace_root=root,
        relative_path=str(path.relative_to(root)),
        path=path,
        content=path.read_text(encoding="utf-8"),
    )


def _write_workspace_file(root: Path, relative_path: str, content: str, *, agent_id: int) -> WorkspaceFileWriteResult:
    path = _resolve_workspace_file_path(root, relative_path, allow_missing=True)
    existed_before = path.exists()
    if path.exists() and path.is_dir():
        raise WorkspacePathError(f"Workspace path points to a directory: {relative_path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    resolved = path.resolve(strict=True)
    _ensure_within_root(resolved, root)
    return WorkspaceFileWriteResult(
        agent_id=agent_id,
        workspace_root=root,
        relative_path=str(resolved.relative_to(root)),
        path=resolved,
        created=not existed_before,
        bytes_written=len(content.encode("utf-8")),
    )


def _delete_workspace_file(root: Path, relative_path: str, *, agent_id: int) -> WorkspaceFileDeleteResult:
    path = _resolve_workspace_file_path(root, relative_path)
    if not path.exists() or not path.is_file():
        raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")
    path.unlink()
    return WorkspaceFileDeleteResult(
        agent_id=agent_id,
        workspace_root=root,
        relative_path=str(path.relative_to(root)),
        path=path,
        deleted=True,
    )


def _resolve_workspace_file_path(
    root: Path,
    relative_path: str,
    *,
    allow_missing: bool = False,
) -> Path:
    safe_relative_path = _validate_relative_path(relative_path)
    target = root / safe_relative_path
    if target.exists():
        resolved = target.resolve(strict=True)
        _ensure_within_root(resolved, root)
        return resolved
    if allow_missing:
        _ensure_within_root(target.parent.resolve(strict=False), root)
        return target
    raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")


def _validate_relative_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if not relative_path or str(path) in {".", ""}:
        raise WorkspacePathError("Workspace path cannot be empty.")
    if path.is_absolute():
        raise WorkspacePathError("Workspace path must be relative.")
    if any(part == ".." for part in path.parts):
        raise WorkspacePathError("Workspace path cannot contain '..'.")
    if path.drive or path.root:
        raise WorkspacePathError("Workspace path must not include a drive or root.")
    return path


def _ensure_within_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WorkspacePathError("Workspace path resolves outside the workspace root.") from exc
