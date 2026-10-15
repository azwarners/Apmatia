"""Unauthenticated, read-only endpoints for explicitly published agents."""

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from apmatia.api.internal.agent_management import _agent_to_dict, list_agents
from apmatia.modules.agents.runtime import get_agent_manager
from apmatia.core.model_management_runtime import get_llm_config_manager

from .agent_routes import _is_publication_eligible

router = APIRouter(prefix="/public/agents", tags=["public-agents"])


class PublicModelReference(BaseModel):
    """Non-secret model mapping for the consumer's configured upstream."""

    id: int = Field(description="Apmatia model-config ID")
    alias: str = Field(description="Apmatia display alias")
    backend: str = Field(description="Configured backend type")
    model: str = Field(description="Provider model name to send to the configured upstream")


class PublicAgent(BaseModel):
    """Stable public-agent contract consumed by external model catalogs."""

    id: int = Field(description="Stable Apmatia agent ID")
    name: str = Field(description="Agent display name")
    system_prompt: str = Field(description="Compiled system prompt")
    model: PublicModelReference | None = Field(
        description="Non-secret backing model mapping, or null if none is configured"
    )


@router.get("", response_model=list[PublicAgent])
def list_public_agents() -> list[dict]:
    return [_public_agent(agent) for agent in list_agents() if _is_published_eligible(agent)]


@router.get("/{agent_id}", response_model=PublicAgent)
def get_public_agent(agent_id: int = Path(..., description="Published agent ID")) -> dict:
    agent = get_agent_manager().get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Public agent not found.")
    agent_data = _agent_to_dict(agent)
    if not _is_published_eligible(agent_data):
        raise HTTPException(status_code=404, detail="Public agent not found.")
    return _public_agent(agent_data)


def _is_published_eligible(agent: object) -> bool:
    is_public = agent.get("is_public", False) if isinstance(agent, dict) else getattr(agent, "is_public", False)
    return bool(is_public) and _is_publication_eligible(agent)


def _public_agent(agent: dict) -> dict:
    """Project an agent onto the intentionally small public response schema."""
    agent_id = int(agent["id"])
    manager = get_agent_manager()
    # The active model is the agent's current selection; default is its fallback.
    model_id = agent.get("active_model_id") or agent.get("default_model_id")
    model_reference = None
    if model_id is not None:
        config = get_llm_config_manager().get_config(int(model_id))
        if config is not None:
            model_reference = {
                "id": config.id,
                "alias": config.user_alias,
                "backend": config.backend,
                "model": config.provider_name,
            }
    return {
        "id": agent_id,
        "name": agent["name"],
        "system_prompt": manager.get_agent_system_prompt(agent_id),
        "model": model_reference,
    }
