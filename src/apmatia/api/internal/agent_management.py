"""Internal API for agent management."""

from apmatia.core.agent_management_runtime import get_agent_manager


# Agent CRUD


def create_agent(name: str, **kwargs) -> dict:
    """Create a new agent."""
    manager = get_agent_manager()
    agent = manager.create_agent(name, **kwargs)
    return _agent_to_dict(agent)


def get_agent(agent_id: int) -> dict | None:
    """Get an agent by ID."""
    manager = get_agent_manager()
    agent = manager.get_agent(agent_id)
    if agent is None:
        return None
    return _agent_to_dict(agent)


def update_agent(agent_id: int, **updates) -> dict:
    """Update an agent."""
    manager = get_agent_manager()
    agent = manager.update_agent(agent_id, **updates)
    return _agent_to_dict(agent)


def delete_agent(agent_id: int) -> bool:
    """Delete an agent by ID."""
    manager = get_agent_manager()
    return manager.delete_agent(agent_id)


def list_agents() -> list[dict]:
    """List all agents."""
    manager = get_agent_manager()
    return [_agent_to_dict(a) for a in manager.list_agents()]


# Helper functions


def _agent_to_dict(agent) -> dict:
    """Convert an Agent to a dictionary."""
    return {
        "id": agent.id,
        "name": agent.name,
        "owner_user_id": getattr(agent, "owner_user_id", None),
        "owner_group_id": getattr(agent, "owner_group_id", None),
        "prompt_id": agent.prompt_id,
        "system_prompt_id": agent.system_prompt_id,
        "memory_id": agent.memory_id,
        "rag_root_ids": agent.rag_root_ids,
        "tool_ids": agent.tool_ids,
        "default_model_id": agent.default_model_id,
        "active_model_id": agent.active_model_id,
        "workspace_root": getattr(agent, "workspace_root", ""),
        "knowledge_root": getattr(agent, "knowledge_root", ""),
        "metadata": agent.metadata,
    }
