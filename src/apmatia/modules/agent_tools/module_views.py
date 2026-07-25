from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution

from .manager import ToolManager
from .models import ToolDefinition


class AgentToolsModuleViewProvider:
    def __init__(self, manager_factory: Callable[[], ToolManager]) -> None:
        self._manager_factory = manager_factory

    @property
    def manager(self) -> ToolManager:
        return self._manager_factory()

    def list_items(self, *, view: ViewContribution, context: ModuleViewContext) -> list[dict[str, Any]]:
        del view, context
        return [_serialize_tool(tool) for tool in self.manager.list_tool_definitions()]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        verb = str(command.metadata.get("verb") or command.command_id.rsplit(".", 1)[-1]).strip().lower()
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}

        values = {
            "name": str(payload.get("name") or "").strip(),
            "description": str(payload.get("description") or ""),
            "provider_id": str(payload.get("provider_id") or "").strip(),
            "enabled": bool(payload.get("enabled", True)),
            "confirmation_required": bool(payload.get("confirmation_required", False)),
            "read_only": bool(payload.get("read_only", True)),
            "input_schema": _json_object(payload.get("input_schema"), field_name="Input schema"),
            "output_schema": _json_object(payload.get("output_schema"), field_name="Output schema"),
            "metadata": _json_object(payload.get("metadata"), field_name="Metadata"),
        }
        if verb == "create":
            tool = self.manager.create_tool_definition(owner_user_id=context.user_id, **values)
            return {"status": "created", "item": _serialize_tool(tool)}
        if verb == "edit":
            tool = self.manager.update_tool_definition(_required_int(payload.get("item_id")), **values)
            return {"status": "updated", "item": _serialize_tool(tool)}
        raise ValueError(f"Unsupported agent tools command verb: {verb}")


def _serialize_tool(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "provider_id": tool.provider_id,
        "enabled": tool.enabled,
        "confirmation_required": tool.confirmation_required,
        "read_only": tool.read_only,
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
        "metadata": tool.metadata,
        "created_at": tool.created_at.isoformat(),
        "updated_at": tool.updated_at.isoformat(),
    }


def _json_object(value: Any, *, field_name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object.")
    return dict(parsed)


def _required_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid agent tool ID is required.") from error


def _view_from_command(command: CommandContribution) -> ViewContribution:
    return ViewContribution(
        module_id=command.module_id,
        action_id=command.action_id,
        view_id=str(command.metadata.get("collection_view_id") or ""),
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )
