from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apmatia.core.modules.workspace import resolve_module_workspace_root


def _agent_loops_base_root() -> Path:
    workspace_root = resolve_module_workspace_root()
    if workspace_root.name == "modules":
        return workspace_root.parent
    return workspace_root


def module_workspace_root() -> Path:
    return _agent_loops_base_root() / "apmatia_agent_loops"


def contacts_root() -> Path:
    return module_workspace_root() / "contacts"


def tasks_root() -> Path:
    return module_workspace_root() / "tasks"


def workspace_root() -> Path:
    return module_workspace_root() / "workspace"


def knowledge_root() -> Path:
    return _agent_loops_base_root() / "knowledge"


@dataclass(frozen=True, slots=True)
class ContactRoots:
    contact_key: str
    workspace_root: Path
    knowledge_root: Path
    task_root: Path


def ensure_module_roots() -> None:
    for root in (contacts_root(), tasks_root(), workspace_root(), knowledge_root()):
        root.mkdir(parents=True, exist_ok=True)


def contact_key(kind: str, contact_id: int | str) -> str:
    return f"{kind}-{contact_id}"


def resolve_contact_roots(kind: str, contact_id: int | str) -> ContactRoots:
    ensure_module_roots()
    key = contact_key(kind, contact_id)
    contact_workspace_root = workspace_root() / key
    contact_knowledge_root = knowledge_root() / key
    contact_task_root = tasks_root() / key
    for root in (contact_workspace_root, contact_knowledge_root, contact_task_root):
        root.mkdir(parents=True, exist_ok=True)
    return ContactRoots(
        contact_key=key,
        workspace_root=contact_workspace_root,
        knowledge_root=contact_knowledge_root,
        task_root=contact_task_root,
    )
