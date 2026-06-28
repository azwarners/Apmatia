from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.lib.agent_management.services import AgentService

from .models import AgentToolAssignment, ToolCall, ToolDefinition, ToolResult
from .registry import ToolRegistry
from .repositories import AgentToolAssignmentRepository, ToolDefinitionRepository


@dataclass(slots=True)
class EffectiveToolAccess:
    tool: ToolDefinition
    assignment: AgentToolAssignment | None
    confirmation_required: bool
    read_only: bool


class ToolExecutor:
    def __init__(
        self,
        tool_repo: ToolDefinitionRepository,
        assignment_repo: AgentToolAssignmentRepository,
        agent_service: AgentService,
        registry: ToolRegistry,
    ) -> None:
        self._tool_repo = tool_repo
        self._assignment_repo = assignment_repo
        self._agent_service = agent_service
        self._registry = registry

    def resolve_tool_access(self, agent_id: int, tool_id: int) -> EffectiveToolAccess | None:
        agent = self._agent_service.get_agent(agent_id)
        if agent is None:
            return None

        tool = self._tool_repo.get(tool_id)
        if tool is None or not tool.enabled:
            return None

        assignment = self._assignment_repo.get_by_agent_tool(agent_id, tool_id)
        legacy_tool_ids = set(agent.tool_ids)

        if assignment is not None:
            if not assignment.enabled:
                return None
            return EffectiveToolAccess(
                tool=tool,
                assignment=assignment,
                confirmation_required=(
                    tool.confirmation_required
                    if assignment.confirmation_required is None
                    else assignment.confirmation_required
                ),
                read_only=tool.read_only if assignment.read_only is None else assignment.read_only,
            )

        if tool_id not in legacy_tool_ids:
            return None

        return EffectiveToolAccess(
            tool=tool,
            assignment=None,
            confirmation_required=tool.confirmation_required,
            read_only=tool.read_only,
        )

    def execute(self, tool_call: ToolCall, *, approval_granted: bool = False) -> ToolResult:
        access = self.resolve_tool_access(tool_call.requester_agent_id, tool_call.tool_id)
        if access is None:
            return ToolResult(
                call_id=tool_call.call_id,
                status="denied",
                error="Tool is unavailable for this agent.",
            )

        validation_errors = validate_json_schema(tool_call.arguments, access.tool.input_schema)
        if validation_errors:
            return ToolResult(
                call_id=tool_call.call_id,
                status="invalid_arguments",
                error="Tool arguments did not match the input schema.",
                metadata={"validation_errors": validation_errors},
            )

        if access.confirmation_required and not approval_granted:
            return ToolResult(
                call_id=tool_call.call_id,
                status="pending_confirmation",
                error="Tool execution requires approval.",
                metadata={"tool_id": access.tool.id, "requester_agent_id": tool_call.requester_agent_id},
            )

        provider = self._registry.get(access.tool.provider_id)
        if provider is None:
            return ToolResult(
                call_id=tool_call.call_id,
                status="error",
                error=f"Tool provider is not registered: {access.tool.provider_id}",
            )

        try:
            result = provider.execute(tool_call.arguments, tool_call=tool_call)
        except Exception as exc:  # pragma: no cover - defensive guard
            return ToolResult(
                call_id=tool_call.call_id,
                status="error",
                error=str(exc),
            )

        output_errors = validate_json_schema(result, access.tool.output_schema)
        if output_errors:
            return ToolResult(
                call_id=tool_call.call_id,
                status="error",
                error="Tool result did not match the output schema.",
                metadata={"validation_errors": output_errors},
            )

        return ToolResult(
            call_id=tool_call.call_id,
            status="success",
            result=result,
            metadata={"tool_id": access.tool.id, "read_only": access.read_only},
        )


def validate_json_schema(value: Any, schema: dict[str, Any] | None, path: str = "$") -> list[str]:
    if not schema:
        return []

    schema_type = schema.get("type")
    if schema_type is not None and not _matches_type(value, schema_type):
        return [f"{path} should be of type {schema_type}"]

    if schema_type == "object":
        if not isinstance(value, dict):
            return [f"{path} should be an object"]
        errors: list[str] = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties", True)

        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} is required")

        for key, item in value.items():
            if key in properties:
                errors.extend(validate_json_schema(item, properties[key], f"{path}.{key}"))
                continue
            if additional is False:
                errors.append(f"{path}.{key} is not allowed")
                continue
            if isinstance(additional, dict):
                errors.extend(validate_json_schema(item, additional, f"{path}.{key}"))
        return errors

    if schema_type == "array":
        if not isinstance(value, list):
            return [f"{path} should be an array"]
        item_schema = schema.get("items")
        if not item_schema:
            return []
        errors: list[str] = []
        for index, item in enumerate(value):
            errors.extend(validate_json_schema(item, item_schema, f"{path}[{index}]"))
        return errors

    return []


def _matches_type(value: Any, schema_type: str | list[str]) -> bool:
    if isinstance(schema_type, list):
        return any(_matches_type(value, item) for item in schema_type)
    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if schema_type == "null":
        return value is None
    return True
