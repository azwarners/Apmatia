"""HTTP routes for agent management."""

from fastapi import APIRouter, Body, HTTPException, Path, Request

from apmatia.api.internal.agent_management import (
    create_agent,
    get_agent,
    update_agent,
    delete_agent,
    list_agents,
)
from apmatia.modules.agents.runtime import get_agent_manager
from apmatia.modules.agents.manager import DEFAULT_AGENT_MODE
from apmatia.core.permissions import can_write

from .shared import member_group_ids, require_session

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=dict)
def create_new_agent(
    request: Request,
    name: str = Body(..., description="Agent name"),
    prompt_id: int | None = Body(None, description="Prompt ID"),
    system_prompt_id: int = Body(0, description="System prompt ID"),
    memory_id: int = Body(0, description="Memory ID"),
    rag_root_ids: list[int] = Body(default_factory=list, description="RAG root IDs"),
    tool_ids: list[int] = Body(default_factory=list, description="Tool IDs"),
    default_model_id: int | None = Body(None, description="Default model ID"),
    active_model_id: int | None = Body(None, description="Active model ID"),
    workspace_root: str = Body("", description="Workspace root"),
    knowledge_root: str = Body("", description="Knowledge root"),
    metadata: dict = Body(default_factory=dict, description="Metadata"),
) -> dict:
    """Create a new agent."""
    session = require_session(request)
    return create_agent(
        name,
        owner_user_id=session.user_id,
        mode=DEFAULT_AGENT_MODE,
        prompt_id=prompt_id,
        system_prompt_id=system_prompt_id,
        memory_id=memory_id,
        rag_root_ids=rag_root_ids,
        tool_ids=tool_ids,
        default_model_id=default_model_id,
        active_model_id=active_model_id,
        workspace_root=workspace_root,
        knowledge_root=knowledge_root,
        metadata=metadata,
    )


@router.get("", response_model=list[dict])
def get_all_agents(request: Request) -> list[dict]:
    """List all agents."""
    require_session(request)
    return list_agents()


@router.get("/{agent_id}", response_model=dict | None)
def get_agent_by_id(
    request: Request,
    agent_id: int = Path(..., description="Agent ID")
) -> dict | None:
    """Get an agent by ID."""
    require_session(request)
    return get_agent(agent_id)


@router.put("/{agent_id}", response_model=dict)
def update_agent_by_id(
    request: Request,
    agent_id: int = Path(..., description="Agent ID"),
    owner_user_id: int | None = Body(None, description="Owner user ID"),
    owner_group_id: int | None = Body(None, description="Owner group ID"),
    name: str | None = Body(None, description="Agent name"),
    prompt_id: int | None = Body(None, description="Prompt ID"),
    system_prompt_id: int | None = Body(None, description="System prompt ID"),
    memory_id: int | None = Body(None, description="Memory ID"),
    rag_root_ids: list[int] | None = Body(None, description="RAG root IDs"),
    tool_ids: list[int] | None = Body(None, description="Tool IDs"),
    default_model_id: int | None = Body(None, description="Default model ID"),
    active_model_id: int | None = Body(None, description="Active model ID"),
    workspace_root: str | None = Body(None, description="Workspace root"),
    knowledge_root: str | None = Body(None, description="Knowledge root"),
    metadata: dict | None = Body(None, description="Metadata"),
) -> dict:
    """Update an agent."""
    session = require_session(request)
    session_group_ids = member_group_ids(session.user_id)
    agent = get_agent_manager().get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    if not _can_update_agent(
        agent,
        session_user_id=session.user_id,
        session_group_ids=session_group_ids,
        owner_user_id=owner_user_id,
        owner_group_id=owner_group_id,
    ):
        raise HTTPException(status_code=403, detail="Agent access denied.")
    updates = {}
    target_owner_user_id = owner_user_id if owner_user_id is not None else getattr(agent, "owner_user_id", None)
    target_owner_group_id = owner_group_id if owner_group_id is not None else getattr(agent, "owner_group_id", None)
    if (
        getattr(agent, "mode", DEFAULT_AGENT_MODE) == 0
        and (
            target_owner_user_id == session.user_id
            or (target_owner_group_id is not None and target_owner_group_id in session_group_ids)
        )
    ):
        updates["mode"] = DEFAULT_AGENT_MODE
    if owner_user_id is not None:
        updates["owner_user_id"] = owner_user_id
    if owner_group_id is not None:
        updates["owner_group_id"] = owner_group_id
    if name is not None:
        updates["name"] = name
    if prompt_id is not None:
        updates["prompt_id"] = prompt_id
    if system_prompt_id is not None:
        updates["system_prompt_id"] = system_prompt_id
    if memory_id is not None:
        updates["memory_id"] = memory_id
    if rag_root_ids is not None:
        updates["rag_root_ids"] = rag_root_ids
    if tool_ids is not None:
        updates["tool_ids"] = tool_ids
    if default_model_id is not None:
        updates["default_model_id"] = default_model_id
    if active_model_id is not None:
        updates["active_model_id"] = active_model_id
    if workspace_root is not None:
        updates["workspace_root"] = workspace_root
    if knowledge_root is not None:
        updates["knowledge_root"] = knowledge_root
    if metadata is not None:
        updates["metadata"] = metadata
    return update_agent(agent_id, **updates)


@router.delete("/{agent_id}", response_model=bool)
def delete_agent_by_id(
    request: Request,
    agent_id: int = Path(..., description="Agent ID")
) -> bool:
    """Delete an agent by ID."""
    require_session(request)
    return delete_agent(agent_id)


def _can_update_agent(
    agent: object,
    *,
    session_user_id: int,
    session_group_ids: set[int],
    owner_user_id: int | None,
    owner_group_id: int | None,
) -> bool:
    if can_write(agent, session_user_id, session_group_ids):
        return True

    if _is_owned_by_session(agent=agent, session_user_id=session_user_id, session_group_ids=session_group_ids):
        return True

    current_owner_user_id = getattr(agent, "owner_user_id", None)
    current_owner_group_id = getattr(agent, "owner_group_id", None)
    if current_owner_user_id is not None or current_owner_group_id is not None:
        return False

    if owner_user_id is not None and owner_user_id != session_user_id:
        return False
    if owner_group_id is not None and owner_group_id not in session_group_ids:
        return False
    return owner_user_id == session_user_id or owner_user_id is None


def _is_owned_by_session(*, agent: object, session_user_id: int, session_group_ids: set[int]) -> bool:
    current_owner_user_id = getattr(agent, "owner_user_id", None)
    if current_owner_user_id is not None and current_owner_user_id == session_user_id:
        return True
    current_owner_group_id = getattr(agent, "owner_group_id", None)
    if current_owner_group_id is not None and current_owner_group_id in session_group_ids:
        return True
    return False
