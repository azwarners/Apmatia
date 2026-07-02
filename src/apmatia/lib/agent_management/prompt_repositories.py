from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Any

from .agent_prompt import AgentPrompt, default_agent_prompt


class AgentPromptRepository(Protocol):
    def create(self, prompt: AgentPrompt) -> int: ...
    def get(self, prompt_id: int) -> AgentPrompt | None: ...
    def update(self, prompt_id: int, prompt: AgentPrompt) -> None: ...
    def list_all(self) -> list[AgentPrompt]: ...


@dataclass(frozen=True, slots=True)
class AgentPromptManagementTables:
    prompts: str = "agent_management_prompts"


class SQLiteAgentPromptRepository:
    def __init__(self, store, tables: AgentPromptManagementTables):
        self._store = store
        self._tables = tables

    def create(self, prompt: AgentPrompt) -> int:
        return self._store.insert(self._tables.prompts, _prompt_to_payload(prompt))

    def get(self, prompt_id: int) -> AgentPrompt | None:
        row = self._store.get(self._tables.prompts, id=prompt_id)
        return None if row is None else _row_to_prompt(row)

    def update(self, prompt_id: int, prompt: AgentPrompt) -> None:
        if self._store.get(self._tables.prompts, id=prompt_id) is None:
            raise ValueError(f"Agent prompt with id {prompt_id} not found.")
        self._store.update(self._tables.prompts, {"id": prompt_id}, _prompt_to_payload(prompt))

    def list_all(self) -> list[AgentPrompt]:
        return [_row_to_prompt(row) for row in self._store.find(self._tables.prompts)]


def _prompt_to_payload(prompt: AgentPrompt) -> dict[str, Any]:
    return {
        "personality": prompt.personality,
        "skills": prompt.skills,
        "purpose": prompt.purpose,
        "backstory": prompt.backstory,
        "communication_style": prompt.communication_style,
        "operating_principles": prompt.operating_principles,
        "autonomy_level": prompt.autonomy_level,
        "decision_making_style": prompt.decision_making_style,
        "memory_policy": prompt.memory_policy,
        "domain_priorities": prompt.domain_priorities,
        "relationship_to_user": prompt.relationship_to_user,
        "tool_use_policy": prompt.tool_use_policy,
        "capability_boundaries": prompt.capability_boundaries,
        "output_preferences": prompt.output_preferences,
        "safety_ethics": prompt.safety_ethics,
        "selfhood_truthfulness": prompt.selfhood_truthfulness,
        "conflict_resolution_rules": prompt.conflict_resolution_rules,
        "use_raw_prompt_override": prompt.use_raw_prompt_override,
        "raw_prompt_override": prompt.raw_prompt_override,
    }


def _row_to_prompt(row: dict) -> AgentPrompt:
    defaults = default_agent_prompt()
    return AgentPrompt(
        personality=str(row.get("personality", defaults.personality)),
        skills=str(row.get("skills", defaults.skills)),
        purpose=str(row.get("purpose", defaults.purpose)),
        backstory=str(row.get("backstory", defaults.backstory)),
        communication_style=str(row.get("communication_style", defaults.communication_style)),
        operating_principles=str(row.get("operating_principles", defaults.operating_principles)),
        autonomy_level=str(row.get("autonomy_level", defaults.autonomy_level)),
        decision_making_style=str(row.get("decision_making_style", defaults.decision_making_style)),
        memory_policy=str(row.get("memory_policy", defaults.memory_policy)),
        domain_priorities=str(row.get("domain_priorities", defaults.domain_priorities)),
        relationship_to_user=str(row.get("relationship_to_user", defaults.relationship_to_user)),
        tool_use_policy=str(row.get("tool_use_policy", defaults.tool_use_policy)),
        capability_boundaries=str(row.get("capability_boundaries", defaults.capability_boundaries)),
        output_preferences=str(row.get("output_preferences", defaults.output_preferences)),
        safety_ethics=str(row.get("safety_ethics", defaults.safety_ethics)),
        selfhood_truthfulness=str(row.get("selfhood_truthfulness", defaults.selfhood_truthfulness)),
        conflict_resolution_rules=str(row.get("conflict_resolution_rules", defaults.conflict_resolution_rules)),
        use_raw_prompt_override=bool(row.get("use_raw_prompt_override", defaults.use_raw_prompt_override)),
        raw_prompt_override=str(row.get("raw_prompt_override", defaults.raw_prompt_override)),
    )
