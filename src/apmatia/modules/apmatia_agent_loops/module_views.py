from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.user_management_runtime import get_group_manager
from apmatia.core.registry import CommandContribution, ViewContribution

from .commands import COMMAND_DESCRIPTORS
from .runner import get_agent_loop_runner
from .state import ContactRoots, resolve_agent_loop_workspace_root


class ApmatiaAgentLoopsModuleViewProvider:
    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root or resolve_agent_loop_workspace_root()

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = str(view.metadata.get("object_type") or "").strip().lower()
        if object_type == "contact":
            return self._list_contacts(context)
        if object_type == "run":
            return self._list_runs(context)
        if object_type == "workspace":
            return self._list_files(context, root_kind="workspace")
        if object_type == "knowledge":
            return self._list_files(context, root_kind="knowledge")
        raise ValueError(f"Unsupported agent loop view type: {object_type}")

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        if command.command_id == "apmatia_agent_loops.tasks.stop":
            task_id = str(payload.get("task_id") or "").strip()
            if not task_id:
                raise ValueError("task_id is required.")
            return get_agent_loop_runner().stop_task(task_id)
        raise ValueError(f"Unsupported agent loop command: {command.command_id}")

    def _list_contacts(self, context: ModuleViewContext) -> list[dict[str, Any]]:
        agent_manager = get_agent_manager()
        group_manager = get_group_manager()
        runner = get_agent_loop_runner()
        tasks = runner.list_tasks()
        task_counts: dict[tuple[str, str], int] = {}
        for task in tasks:
            key = (str(task.get("contact_kind") or ""), str(task.get("contact_id") or ""))
            task_counts[key] = task_counts.get(key, 0) + 1

        items: list[dict[str, Any]] = []
        for agent in agent_manager.list_agents():
            roots = self._contact_roots("agent", agent.id)
            key = ("agent", str(agent.id))
            items.append(
                {
                    "id": f"agent:{agent.id}",
                    "title": agent.name,
                    "contact_kind": "agent",
                    "contact_id": agent.id,
                    "task_count": task_counts.get(key, 0),
                    "workspace_root": str(roots.workspace_root),
                    "knowledge_root": str(roots.knowledge_root),
                    "updated_at": _to_display_text(getattr(agent, "updated_at", None)),
                }
            )
        for group in group_manager.list_groups():
            roots = self._contact_roots("group", group.id)
            key = ("group", str(group.id))
            items.append(
                {
                    "id": f"group:{group.id}",
                    "title": group.name,
                    "contact_kind": "group",
                    "contact_id": group.id,
                    "task_count": task_counts.get(key, 0),
                    "workspace_root": str(roots.workspace_root),
                    "knowledge_root": str(roots.knowledge_root),
                    "updated_at": _to_display_text(getattr(group, "updated_at", None)),
                }
            )
        return items

    def _list_runs(self, context: ModuleViewContext) -> list[dict[str, Any]]:
        tasks = get_agent_loop_runner().list_tasks()
        items: list[dict[str, Any]] = []
        for task in tasks:
            metadata = dict(task.get("metadata") or {})
            items.append(
                {
                    "id": task.get("id"),
                    "task_id": task.get("id"),
                    "title": task.get("title"),
                    "status": task.get("status"),
                    "contact_kind": task.get("contact_kind"),
                    "contact_id": task.get("contact_id"),
                    "prompt": task.get("prompt"),
                    "checklist": task.get("checklist") or [],
                    "current_iteration": task.get("current_turn"),
                    "max_iterations": task.get("max_model_turns"),
                    "loop_status": metadata.get("loop_status") if isinstance(metadata.get("loop_status"), dict) else {},
                    "summary": task.get("summary"),
                    "final_text": task.get("final_text"),
                    "executive_analysis": metadata.get("executive_analysis") or "",
                    "metadata": metadata,
                    "workspace_root": task.get("workspace_root"),
                    "knowledge_root": task.get("knowledge_root"),
                    "events": task.get("events", []),
                    "updated_at": task.get("updated_at"),
                    "created_at": task.get("created_at"),
                    "contact": task.get("contact"),
                }
            )
        return items

    def _list_files(self, context: ModuleViewContext, *, root_kind: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for task in get_agent_loop_runner().list_tasks():
            roots = self._contact_roots(str(task.get("contact_kind") or ""), task.get("contact_id"))
            root = roots.workspace_root if root_kind == "workspace" else roots.knowledge_root
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                items.append(
                    {
                        "path": str(path),
                        "kind": root_kind,
                        "task_id": task.get("id"),
                    }
                )
        return items

    def _contact_roots(self, contact_kind: str, contact_id: str | int) -> ContactRoots:
        normalized_kind = str(contact_kind or "contact").strip().lower() or "contact"
        normalized_id = str(contact_id or "").strip() or "unknown"
        slug = f"{normalized_kind}-{normalized_id}"
        return ContactRoots(
            workspace_root=self._workspace_root / "workspace" / slug,
            knowledge_root=self._workspace_root / "knowledge" / slug,
            task_root=self._workspace_root / "tasks" / slug,
        )


def _to_display_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)
