"""API-owned providers for rich, renderer-neutral view data sources."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from apmatia.api.internal.agent_loops import get_loop_task, list_loop_tasks
from apmatia.api.internal.agent_management import list_agents
from apmatia.api.internal.group_access import enabled_group_ids
from apmatia.api.internal.users import list_user_groups
from apmatia.modules.agent_loops.module_views import ApmatiaAgentLoopsModuleViewProvider
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.modules.discuss.services import DISCUSS_DB, TopicManagementService, get_discussion
from apmatia.api.internal.model_management import list_llm_configs


def load_view_source(operation: str, *, user_id: int, parameters: dict[str, Any] | None = None) -> Any:
    """Resolve a declared source operation without exposing module internals to clients."""
    params = dict(parameters or {})
    if operation in {"agents:list", "list_agents"}:
        return [_serialize(agent) for agent in list_agents()]
    if operation in {"model_configs:list", "list_llm_configs"}:
        return [_serialize(config) for config in list_llm_configs()]
    if operation == "discussion_tree":
        return _discussion_tree()
    if operation == "discussion_state":
        discussion_id = params.get("discussion_id")
        return _discussion_state(str(discussion_id)) if discussion_id else {}
    if operation == "discussion_activity":
        state = load_view_source("discussion_state", user_id=user_id, parameters=params)
        return state.get("activity", {}) if isinstance(state, dict) else {}
    if operation in {"list_contacts", "list_tasks", "list_workspace_files", "list_knowledge_files"}:
        provider = ApmatiaAgentLoopsModuleViewProvider()
        view_type = {
            "list_contacts": "contact",
            "list_tasks": "run",
            "list_workspace_files": "workspace",
            "list_knowledge_files": "knowledge",
        }[operation]
        view = type("SourceView", (), {"metadata": {"object_type": view_type}})()
        return provider.list_items(
            view=view,
            context=ModuleViewContext(user_id=user_id, group_ids=frozenset(enabled_group_ids(list_user_groups(user_id)))),
        )
    if operation == "get_current_task":
        task_id = params.get("task_id")
        return get_loop_task(str(task_id)) if task_id else {}
    raise ValueError(f"Unsupported view source operation: {operation}")


def _discussion_tree() -> dict[str, Any]:
    discussions = []
    try:
        discussions = [
            _serialize(item)
            for item in DISCUSS_DB.list_discussions()
        ]
    except (AttributeError, TypeError):
        pass
    return {"current_discussion_id": None, "folders": [], "discussions": discussions}


def _discussion_state(discussion_id: str) -> dict[str, Any]:
    try:
        value = get_discussion(discussion_id)
    except (KeyError, TypeError, ValueError):
        value = None
    if value is None:
        return {"discussion_id": discussion_id, "messages": [], "activity": {}}
    serialized = _serialize(value)
    if isinstance(serialized, dict):
        serialized.setdefault("discussion_id", discussion_id)
        turns = TopicManagementService().list_turns(discussion_id=discussion_id)
        serialized["messages"] = [_serialize(turn) for turn in turns]
        serialized["items"] = serialized["messages"]
        serialized.setdefault("activity", {})
        return serialized
    return {"discussion_id": discussion_id, "messages": []}


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
