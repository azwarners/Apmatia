from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from apmatia.modules.agents.services import AgentService
from apmatia.core.modules import (
    InvalidModuleSlugError,
    ModuleAlreadyExistsError,
    WorkspaceFileNotFoundError,
    WorkspaceModuleNotFoundError,
    WorkspacePathError,
    WorkspaceRootError,
    WorkspaceRootNotFoundError,
    WorkspaceRootPermissionError,
)

from .audit import record_tool_call_event
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

        if tool.provider_id == "builtin.agent_loops_list_agents":
            return EffectiveToolAccess(
                tool=tool,
                assignment=None,
                confirmation_required=tool.confirmation_required,
                read_only=True,
            )

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
        requested_tool = self._tool_repo.get(tool_call.tool_id)
        request_id = tool_call.call_id or f"call_{uuid4().hex}"
        access = self.resolve_tool_access(tool_call.requester_agent_id, tool_call.tool_id)
        if access is None:
            result = ToolResult(
                call_id=request_id,
                status="denied",
                error=_tool_error(
                    code="TOOL_UNAVAILABLE",
                    message="Tool is unavailable for this agent.",
                    tool_name=None if requested_tool is None else requested_tool.name,
                    request_id=request_id,
                    remediation="Assign the tool to the agent or enable it for the current discussion.",
                ),
            )
            self._record_tool_call(tool_call, result, approval_granted=approval_granted, tool=requested_tool)
            return result

        validation_errors = validate_json_schema(tool_call.arguments, access.tool.input_schema)
        if validation_errors:
            result = ToolResult(
                call_id=request_id,
                status="invalid_arguments",
                error=_tool_error(
                    code="VALIDATION_ERROR",
                    message="Tool arguments did not match the input schema.",
                    tool_name=access.tool.name,
                    request_id=request_id,
                    remediation="Fix the arguments so they match the input schema.",
                    validation_errors=validation_errors,
                ),
                metadata={"validation_errors": validation_errors},
            )
            self._record_tool_call(tool_call, result, approval_granted=approval_granted, tool=access.tool)
            return result

        if access.confirmation_required and not approval_granted:
            result = ToolResult(
                call_id=request_id,
                status="pending_confirmation",
                error=_tool_error(
                    code="APPROVAL_REQUIRED",
                    message="Tool execution requires approval.",
                    tool_name=access.tool.name,
                    request_id=request_id,
                    remediation="Approve the request and retry the tool call.",
                ),
                metadata={"tool_id": access.tool.id, "requester_agent_id": tool_call.requester_agent_id},
            )
            self._record_tool_call(tool_call, result, approval_granted=approval_granted, tool=access.tool)
            return result

        provider = self._registry.get(access.tool.provider_id)
        if provider is None:
            result = ToolResult(
                call_id=request_id,
                status="error",
                error=_tool_error(
                    code="PROVIDER_NOT_REGISTERED",
                    message=f"Tool provider is not registered: {access.tool.provider_id}",
                    tool_name=access.tool.name,
                    request_id=request_id,
                    remediation="Register the provider before executing this tool.",
                ),
            )
            self._record_tool_call(tool_call, result, approval_granted=approval_granted, tool=access.tool)
            return result

        try:
            result = provider.execute(tool_call.arguments, tool_call=tool_call)
        except Exception as exc:  # pragma: no cover - defensive guard
            tool_result = ToolResult(
                call_id=request_id,
                status="error",
                error=_tool_exception_to_error(
                    exc,
                    tool_name=access.tool.name,
                    request_id=request_id,
                ),
            )
            self._record_tool_call(tool_call, tool_result, approval_granted=approval_granted, tool=access.tool)
            return tool_result

        output_errors = validate_json_schema(result, access.tool.output_schema)
        if output_errors:
            tool_result = ToolResult(
                call_id=request_id,
                status="error",
                error=_tool_error(
                    code="INVALID_TOOL_RESULT",
                    message="Tool result did not match the output schema.",
                    tool_name=access.tool.name,
                    request_id=request_id,
                    remediation="Update the provider output so it matches the declared schema.",
                    validation_errors=output_errors,
                ),
                metadata={"validation_errors": output_errors},
            )
            self._record_tool_call(tool_call, tool_result, approval_granted=approval_granted, tool=access.tool)
            return tool_result

        tool_result = ToolResult(
            call_id=request_id,
            status="success",
            result=result,
            metadata={"tool_id": access.tool.id, "read_only": access.read_only},
        )
        self._record_tool_call(tool_call, tool_result, approval_granted=approval_granted, tool=access.tool)
        return tool_result

    def _record_tool_call(
        self,
        tool_call: ToolCall,
        result: ToolResult,
        *,
        approval_granted: bool,
        tool: ToolDefinition | None = None,
    ) -> None:
        payload = {
            "call_id": tool_call.call_id,
            "tool_id": tool_call.tool_id,
            "tool_name": None if tool is None else tool.name,
            "provider_id": None if tool is None else tool.provider_id,
            "requester_agent_id": tool_call.requester_agent_id,
            "discussion_id": tool_call.discussion_id,
            "approval_granted": approval_granted,
            "status": result.status,
            "error": result.error,
            "arguments": tool_call.arguments,
            "result": result.result,
            "metadata": result.metadata,
        }
        try:
            record_tool_call_event(payload)
        except Exception:  # pragma: no cover - logging must never break execution
            return


def _tool_error(
    *,
    code: str,
    message: str,
    tool_name: str | None,
    request_id: str,
    remediation: str = "",
    **details: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "tool_name": tool_name,
        "request_id": request_id,
    }
    if remediation:
        payload["remediation"] = remediation
    for key, value in details.items():
        if value is not None:
            payload[key] = value
    return payload


def _tool_exception_to_error(exc: Exception, *, tool_name: str, request_id: str) -> dict[str, Any]:
    if isinstance(exc, WorkspaceRootNotFoundError):
        return _tool_error(
            code="MISSING_WORKSPACE_DIRECTORY",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Create the workspace directory or mount the persistent workspace volume.",
        )
    if isinstance(exc, WorkspaceRootPermissionError):
        return _tool_error(
            code="PERMISSION_DENIED",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Fix workspace volume permissions so Apmatia can write to the workspace root.",
        )
    if isinstance(exc, WorkspaceRootError):
        return _tool_error(
            code="WORKSPACE_ROOT_ERROR",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Check the workspace root configuration.",
        )
    if isinstance(exc, WorkspaceModuleNotFoundError):
        return _tool_error(
            code="WORKSPACE_MODULE_NOT_FOUND",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Create the workspace module before trying to access it.",
        )
    if isinstance(exc, WorkspaceFileNotFoundError):
        return _tool_error(
            code="WORKSPACE_FILE_NOT_FOUND",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Check the relative path or create the file first.",
        )
    if isinstance(exc, WorkspacePathError):
        return _tool_error(
            code="WORKSPACE_PATH_ERROR",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Use a relative path inside the module root.",
        )
    if isinstance(exc, ModuleAlreadyExistsError):
        return _tool_error(
            code="MODULE_ALREADY_EXISTS",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Choose a new module slug or rerun with force if overwriting is intended.",
        )
    if isinstance(exc, InvalidModuleSlugError):
        return _tool_error(
            code="INVALID_MODULE_SLUG",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Use a lowercase slug that starts with a letter and only contains letters, numbers, or underscores.",
        )
    if isinstance(exc, PermissionError):
        return _tool_error(
            code="PERMISSION_DENIED",
            message=str(exc),
            tool_name=tool_name,
            request_id=request_id,
            remediation="Check filesystem permissions and volume mounts.",
        )
    return _tool_error(
        code="TOOL_EXECUTION_ERROR",
        message=str(exc),
        tool_name=tool_name,
        request_id=request_id,
        remediation="Inspect the tool implementation and retry.",
        exception_type=type(exc).__name__,
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
