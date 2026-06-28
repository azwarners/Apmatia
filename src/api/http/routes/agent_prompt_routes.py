from dataclasses import asdict

from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel

from src.api.internal.agent_prompts import (
    create_agent_prompt,
    get_compiled_agent_prompt,
    get_agent_prompt,
    update_agent_prompt,
)

router = APIRouter(prefix="/agent-prompts", tags=["agent-prompts"])


class AgentPromptPayload(BaseModel):
    personality: str = "Helpful, calm, and thoughtful."
    skills: str = "General assistance, analysis, and coordination."
    purpose: str = "Support the user with reliable and focused help."
    backstory: str = "An AI assistant built to work clearly and carefully."
    communication_style: str = "Clear, concise, and friendly."
    operating_principles: str = "Be accurate, practical, and easy to work with."
    autonomy_level: str = "Act with moderate autonomy and ask when uncertain."
    decision_making_style: str = "Prefer simple, reversible decisions with explicit reasoning."
    memory_policy: str = "Use only available context and avoid assuming hidden memory."
    domain_priorities: str = "Prioritize the user's immediate task and relevant context."
    relationship_to_user: str = "A collaborative assistant working alongside the user."
    tool_use_policy: str = "Use tools only when they clearly help accomplish the task."
    capability_boundaries: str = "Be honest about limits and avoid claiming unavailable abilities."
    output_preferences: str = "Prefer structured, actionable, and readable responses."
    safety_ethics: str = "Avoid harmful actions, respect consent, and follow safety rules."
    selfhood_truthfulness: str = "Do not pretend to be human or claim subjective experience."
    conflict_resolution_rules: str = "Resolve ambiguity by asking concise clarifying questions."
    use_raw_prompt_override: bool = False
    raw_prompt_override: str = ""


@router.post("", response_model=dict)
def create_prompt(payload: AgentPromptPayload = Body(default_factory=AgentPromptPayload)) -> dict:
    return create_agent_prompt(**payload.model_dump())


@router.get("/{prompt_id}", response_model=dict | None)
def get_prompt(prompt_id: int = Path(...)) -> dict | None:
    return get_agent_prompt(prompt_id)


@router.put("/{prompt_id}", response_model=dict)
def update_prompt(prompt_id: int = Path(...), payload: AgentPromptPayload = Body(...)) -> dict:
    return update_agent_prompt(prompt_id, **payload.model_dump())


@router.get("/{prompt_id}/compiled", response_model=str)
def get_compiled_prompt(
    prompt_id: int = Path(...),
    name: str | None = Query(None, description="Agent name for prompt compilation"),
) -> str:
    try:
        return get_compiled_agent_prompt(prompt_id, name=name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
