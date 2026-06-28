"""Internal API for tool management."""

from src.core.tool_management_runtime import get_tool_manager
from src.lib.tool_management.models import ToolCall, ToolResult, new_tool_call_id


def create_tool_definition(**kwargs) -> dict:
    tool = get_tool_manager().create_tool_definition(**kwargs)
    return _tool_definition_to_dict(tool)


def get_tool_definition(tool_id: int) -> dict | None:
    tool = get_tool_manager().get_tool_definition(tool_id)
    if tool is None:
        return None
    return _tool_definition_to_dict(tool)


def update_tool_definition(tool_id: int, **updates) -> dict:
    tool = get_tool_manager().update_tool_definition(tool_id, **updates)
    return _tool_definition_to_dict(tool)


def list_tool_definitions() -> list[dict]:
    return [_tool_definition_to_dict(tool) for tool in get_tool_manager().list_tool_definitions()]


def assign_tool_to_agent(
    agent_id: int,
    tool_id: int,
    *,
    enabled: bool = True,
    confirmation_required: bool | None = None,
    read_only: bool | None = None,
) -> dict:
    assignment = get_tool_manager().assign_tool_to_agent(
        agent_id,
        tool_id,
        enabled=enabled,
        confirmation_required=confirmation_required,
        read_only=read_only,
    )
    return _assignment_to_dict(assignment)


def unassign_tool_from_agent(agent_id: int, tool_id: int) -> bool:
    return get_tool_manager().unassign_tool_from_agent(agent_id, tool_id)


def list_agent_tool_assignments(agent_id: int) -> list[dict]:
    return [_assignment_to_dict(item) for item in get_tool_manager().list_agent_tool_assignments(agent_id)]


def list_tools_available_to_agent(agent_id: int) -> list[dict]:
    return [_tool_definition_to_dict(tool) for tool in get_tool_manager().list_tools_available_to_agent(agent_id)]


def execute_tool_call(
    tool_id: int,
    arguments: dict,
    requester_agent_id: int,
    *,
    discussion_id: str | None = None,
    call_id: str | None = None,
    approval_granted: bool = False,
) -> dict:
    result = get_tool_manager().execute_tool_call(
        ToolCall(
            tool_id=tool_id,
            arguments=arguments,
            requester_agent_id=requester_agent_id,
            discussion_id=discussion_id,
            call_id=call_id or new_tool_call_id(),
        ),
        approval_granted=approval_granted,
    )
    return _tool_result_to_dict(result)


def _tool_definition_to_dict(tool) -> dict:
    return {
        "id": tool.id,
        "owner_user_id": tool.owner_user_id,
        "owner_group_id": tool.owner_group_id,
        "mode": tool.mode,
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
        "output_schema": tool.output_schema,
        "provider_id": tool.provider_id,
        "enabled": tool.enabled,
        "confirmation_required": tool.confirmation_required,
        "read_only": tool.read_only,
        "metadata": tool.metadata,
        "created_at": tool.created_at.isoformat(),
        "updated_at": tool.updated_at.isoformat(),
    }


def _assignment_to_dict(assignment) -> dict:
    return {
        "id": assignment.id,
        "agent_id": assignment.agent_id,
        "tool_id": assignment.tool_id,
        "enabled": assignment.enabled,
        "confirmation_required": assignment.confirmation_required,
        "read_only": assignment.read_only,
    }


def _tool_result_to_dict(result: ToolResult) -> dict:
    return {
        "call_id": result.call_id,
        "status": result.status,
        "result": result.result,
        "error": result.error,
        "metadata": result.metadata,
    }
