from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apmatia.core.modules.workspace import resolve_module_workspace_root


@dataclass(frozen=True, slots=True)
class ContactRoots:
    workspace_root: Path
    knowledge_root: Path
    task_root: Path


def resolve_agent_loop_workspace_root(base_dir: Path | None = None) -> Path:
    return resolve_module_workspace_root(base_dir) / "agent_loops"


def resolve_contact_roots(contact_kind: str, contact_id: str | int) -> ContactRoots:
    normalized_kind = str(contact_kind or "contact").strip().lower() or "contact"
    normalized_id = str(contact_id or "").strip() or "unknown"
    root = resolve_agent_loop_workspace_root()
    slug = f"{normalized_kind}-{normalized_id}"
    return ContactRoots(
        workspace_root=root / "workspace" / slug,
        knowledge_root=root / "knowledge" / slug,
        task_root=root / "tasks" / slug,
    )
