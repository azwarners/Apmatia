from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.core.user_management_runtime import get_group_manager
from apmatia.lib.discussions import discussion_state

from .runner import get_agent_loop_runner
from .records import list_task_records
from .state import contact_key, knowledge_root, resolve_contact_roots, workspace_root


class ApmatiaAgentLoopsModuleViewProvider:
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        if object_type == "contact":
            return _list_contacts(context=context)
        if object_type == "run":
            return _list_runs(context=context)
        if object_type == "workspace":
            return _list_files(context=context, root_factory=workspace_root, kind="workspace")
        if object_type == "knowledge":
            return _list_files(context=context, root_factory=knowledge_root, kind="knowledge")
        raise ValueError(f"Unsupported agent loops object type: {object_type}")

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        if object_type not in {"contact", "run", "workspace", "knowledge"}:
            raise ValueError(f"Unsupported agent loops object type: {object_type}")

        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb == "stop" and object_type == "run":
            task_id = str(payload.get("task_id") or "").strip()
            if not task_id:
                raise ValueError("task_id is required to stop a run.")
            runner = get_agent_loop_runner()
            return runner.stop_task(task_id)
        raise ValueError(f"Unsupported module command verb for now: {verb}")


def _list_contacts(*, context: ModuleViewContext) -> list[dict[str, Any]]:
    agent_manager = get_agent_manager()
    group_manager = get_group_manager()
    task_records = _task_records(context)

    contact_stats: dict[str, dict[str, Any]] = {}
    for record in task_records:
        contact_stats.setdefault(contact_key(record.contact_kind, record.contact_id), {"task_count": 0})
        contact_stats[contact_key(record.contact_kind, record.contact_id)]["task_count"] += 1

    contacts: list[dict[str, Any]] = []
    for agent in agent_manager.list_agents():
        agent_id = getattr(agent, "id", None)
        if agent_id is None:
            continue
        roots = resolve_contact_roots("agent", agent_id)
        model_id = getattr(agent, "active_model_id", None) or getattr(agent, "default_model_id", None)
        stats = contact_stats.get(contact_key("agent", agent_id), {})
        contacts.append(
            {
                "id": f"agent:{agent_id}",
                "contact_kind": "agent",
                "contact_id": agent_id,
                "title": str(getattr(agent, "name", "") or f"Agent {agent_id}"),
                "kind": "Agent",
                "detail": f"Model {model_id}" if model_id is not None else "No model selected",
                "task_count": stats.get("task_count", 0),
                "workspace": str(roots.workspace_root),
                "knowledge": str(roots.knowledge_root),
                "updated_at": _iso(getattr(agent, "updated_at", None)),
            }
        )

    for group in group_manager.list_groups():
        group_id = getattr(group, "id", None)
        if group_id is None:
            continue
        roots = resolve_contact_roots("group", group_id)
        stats = contact_stats.get(contact_key("group", group_id), {})
        contacts.append(
            {
                "id": f"group:{group_id}",
                "contact_kind": "group",
                "contact_id": group_id,
                "title": str(getattr(group, "name", "") or f"Group {group_id}"),
                "kind": "Group",
                "detail": str(getattr(group, "description", "") or "Shared workspace"),
                "task_count": stats.get("task_count", 0),
                "workspace": str(roots.workspace_root),
                "knowledge": str(roots.knowledge_root),
                "updated_at": _iso(getattr(group, "updated_at", None)),
            }
        )

    contacts.sort(key=lambda item: (str(item.get("kind") or ""), str(item.get("title") or "").lower()))
    return contacts


def _list_runs(*, context: ModuleViewContext) -> list[dict[str, Any]]:
    if context.user_id is None:
        return []

    task_records = _task_records(context)
    agent_names = {str(agent.get("id")): str(agent.get("name") or f"Agent {agent.get('id')}") for agent in _raw_agents()}
    runs: list[dict[str, Any]] = []

    for record in task_records:
        if record.contact_kind == "agent":
            contact = agent_names.get(str(record.contact_id), f"Agent {record.contact_id}")
        elif record.participant_agent_ids:
            contact = ", ".join(agent_names.get(str(agent_id), f"Agent {agent_id}") for agent_id in record.participant_agent_ids)
        else:
            contact = f"Group {record.contact_id}"
        roots = resolve_contact_roots(record.contact_kind, record.contact_id)

        runs.append(
            {
                "id": record.task_id,
                "task_id": record.task_id,
                "contact_kind": record.contact_kind,
                "contact_id": record.contact_id,
                "title": str(record.title or "Untitled Loop Task"),
                "contact": contact,
                "status": str(record.status or "queued"),
                "mode": str(record.chat_mode or "single"),
                "prompt": str(record.prompt or ""),
                "discussion_id": str(record.discussion_id or ""),
                "current_iteration": record.current_iteration,
                "max_iterations": record.max_iterations,
                "stop_requested": bool(record.stop_requested),
                "loop_status": dict(record.loop_status or {}),
                "workspace": str(roots.workspace_root),
                "knowledge": str(roots.knowledge_root),
                "summary": str(record.summary or ""),
                "executive_analysis": str(record.executive_analysis or ""),
                "last_error": str(record.last_error or ""),
                "checklist": [dict(item) for item in record.checklist],
                "events": [dict(item) for item in record.events],
                "updated_at": _iso(record.updated_at),
                "created_at": _iso(record.created_at),
                "completed_at": _iso(record.completed_at),
                "workspace_root": str(record.workspace_root or roots.workspace_root),
                "knowledge_root": str(record.knowledge_root or roots.knowledge_root),
            }
        )

    runs.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return runs


def _list_files(
    *,
    context: ModuleViewContext,
    root_factory: Any,
    kind: str,
) -> list[dict[str, Any]]:
    if context.user_id is None:
        return []

    items: list[dict[str, Any]] = []
    for roots in _contact_roots_for_context(context):
        root = root_factory() / roots.contact_key
        root.mkdir(parents=True, exist_ok=True)
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
                updated_at = path.stat().st_mtime
            except OSError:
                size = 0
                updated_at = None
            items.append(
                {
                    "path": str(path),
                    "kind": kind,
                    "size": size,
                    "updated_at": _iso(updated_at),
                }
            )
    items.sort(key=lambda item: str(item.get("path") or "").lower())
    return items


def _contact_roots_for_context(context: ModuleViewContext) -> list[Any]:
    task_records = _task_records(context)
    roots: dict[str, Any] = {}
    for record in task_records:
        roots[contact_key(record.contact_kind, record.contact_id)] = resolve_contact_roots(record.contact_kind, record.contact_id)
    return list(roots.values())


def _discussion_tree(context: ModuleViewContext) -> list[dict[str, Any]]:
    if context.user_id is None:
        return []
    tree = discussion_state.list_tree(user_id=context.user_id, member_group_ids=set(context.group_ids))
    return list(tree.get("discussions", []))


def _task_records(context: ModuleViewContext) -> list[Any]:
    if context.user_id is None:
        return []
    return [record for record in list_task_records() if int(record.owner_user_id) == int(context.user_id)]


def _raw_agents() -> list[dict[str, Any]]:
    agents = []
    for agent in get_agent_manager().list_agents():
        agents.append(
            {
                "id": getattr(agent, "id", None),
                "name": getattr(agent, "name", None),
            }
        )
    return agents


def _object_type(metadata: Mapping[str, Any]) -> str:
    object_type = str(metadata.get("object_type") or "").strip()
    if not object_type:
        raise ValueError("Module metadata is missing object_type.")
    return object_type


def _command_verb(command_id: str) -> str:
    parts = [part for part in str(command_id).split(".") if part]
    return "" if not parts else parts[-1].lower()


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _view_from_command(command: CommandContribution) -> ViewContribution:
    view_id = str(command.metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=command.action_id,
        view_id=view_id,
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )
