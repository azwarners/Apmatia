from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from apmatia.core.agent_management_runtime import get_agent_manager
from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from apmatia.lib.agent_management.models import Agent


class ApmatiaAgentConfigModuleViewProvider:
    def __init__(self, agent_manager: Any | None = None) -> None:
        self._agent_manager = agent_manager

    @property
    def agent_manager(self) -> Any:
        if self._agent_manager is None:
            self._agent_manager = get_agent_manager()
        return self._agent_manager

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        del context
        del view
        agents = sorted(self.agent_manager.list_agents(), key=lambda agent: (str(agent.name).lower(), int(agent.id or 0)))
        return [_serialize_agent(agent) for agent in agents]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        del context
        verb = str(command.metadata.get("verb") or "").strip().lower()
        if verb != "save":
            raise ValueError(f"Unsupported module command verb for now: {verb}")

        agent_id = _require_int(payload.get("agent_id"))
        workspace_root = str(payload.get("workspace_root") or "").strip()
        knowledge_root = str(payload.get("knowledge_root") or "").strip()
        agent = self.agent_manager.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        warnings = _access_warnings(workspace_root, label="workspace root")
        warnings.extend(_access_warnings(knowledge_root, label="knowledge root"))

        updated = self.agent_manager.update_agent(
            agent_id,
            workspace_root=workspace_root,
            knowledge_root=knowledge_root,
        )
        result: dict[str, Any] = {
            "status": "updated",
            "message": f"Saved configuration for {updated.name}.",
            "item": _serialize_agent(updated),
            "warnings": warnings,
        }
        if warnings:
            result["warning"] = "Configuration saved, but one or more paths may not be accessible yet."
        return result


def _serialize_agent(agent: Agent) -> dict[str, Any]:
    workspace_status = _path_status(agent.workspace_root, label="workspace root")
    knowledge_status = _path_status(agent.knowledge_root, label="knowledge root")
    return {
        "id": agent.id,
        "name": agent.name,
        "workspace_root": agent.workspace_root,
        "knowledge_root": agent.knowledge_root,
        "workspace_root_status": workspace_status,
        "knowledge_root_status": knowledge_status,
    }


def _access_warnings(path_value: str, *, label: str) -> list[str]:
    path = path_value.strip()
    if not path:
        return []

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return [f"{label.title()} should be an absolute path: {path}"]
    if not candidate.exists():
        return [f"{label.title()} does not exist yet: {path}"]
    if not candidate.is_dir():
        return [f"{label.title()} is not a directory: {path}"]
    if not os.access(candidate, os.R_OK | os.X_OK):
        return [f"{label.title()} is not readable by the current process: {path}"]
    if not os.access(candidate, os.W_OK | os.X_OK):
        return [f"{label.title()} is not writable by the current process: {path}"]
    return []


def _path_status(path_value: str, *, label: str) -> str:
    path = path_value.strip()
    if not path:
        return "Not set"

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return "Relative path"
    if not candidate.exists():
        return "Missing"
    if not candidate.is_dir():
        return "Not a directory"
    if not os.access(candidate, os.R_OK | os.X_OK):
        return "Not readable"
    if not os.access(candidate, os.W_OK | os.X_OK):
        return "Not writable"
    return "Ready"


def _require_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid agent ID is required.") from error
