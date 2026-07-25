from __future__ import annotations

from dataclasses import replace
from typing import Any

from apmatia.core.workspaces import resolve_agent_workspace_root
from apmatia.core.models import utc_now

from .agent_prompt import AgentPrompt, compile_agent_system_prompt, default_agent_prompt
from .models import Agent
from .repositories import AgentRepository
from .services import AgentService
from .prompt_repositories import AgentPromptRepository


DEFAULT_AGENT_MODE = 0o600


class AgentManager(AgentService):
    """
    Core orchestration entrypoint for agent lifecycle operations.
    """

    def __init__(self, agent_repo: AgentRepository, prompt_repo: AgentPromptRepository | None = None):
        self._agent_repo = agent_repo
        self._prompt_repo = prompt_repo

    def create_prompt(self, prompt: AgentPrompt | None = None, **kwargs) -> tuple[AgentPrompt, int]:
        prompt_obj = prompt or AgentPrompt(**kwargs) if kwargs else default_agent_prompt()
        if self._prompt_repo is None:
            raise ValueError("Prompt repository is not configured.")
        prompt_id = self._prompt_repo.create(prompt_obj)
        return prompt_obj, prompt_id

    def get_prompt(self, prompt_id: int) -> AgentPrompt | None:
        if self._prompt_repo is None:
            return None
        return self._prompt_repo.get(prompt_id)

    def update_prompt(self, prompt_id: int, **updates) -> AgentPrompt:
        if self._prompt_repo is None:
            raise ValueError("Prompt repository is not configured.")
        existing = self._prompt_repo.get(prompt_id)
        if existing is None:
            raise ValueError(f"Agent prompt not found: {prompt_id}")
        updated = replace(existing, **updates)
        self._prompt_repo.update(prompt_id, updated)
        return updated

    def compile_agent_system_prompt(self, name: str, prompt: AgentPrompt) -> str:
        return compile_agent_system_prompt(name, prompt)

    def get_agent_system_prompt(self, agent_id: int) -> str:
        agent = self.get_agent(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")
        prompt = self._resolve_agent_prompt(agent)
        return compile_agent_system_prompt(agent.name, prompt)

    def create_agent(self, name: str, **kwargs) -> Agent:
        """Create a new agent."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Agent name cannot be empty.")

        # Check if agent already exists
        existing = self._agent_repo.get_by_name(clean_name)
        if existing:
            raise ValueError(f"Agent already exists: {clean_name}")

        prompt_id = kwargs.get("prompt_id")
        if prompt_id is None and self._prompt_repo is not None:
            prompt_payload = {k: kwargs[k] for k in _PROMPT_FIELDS if k in kwargs}
            prompt_obj = AgentPrompt(**prompt_payload) if prompt_payload else default_agent_prompt()
            prompt_id = self._prompt_repo.create(prompt_obj)

        agent = Agent(
            id=None,
            owner_user_id=kwargs.get("owner_user_id"),
            owner_group_id=kwargs.get("owner_group_id"),
            mode=kwargs.get("mode", DEFAULT_AGENT_MODE),
            name=clean_name,
            prompt_id=prompt_id,
            system_prompt_id=kwargs.get("system_prompt_id", 0),
            memory_id=kwargs.get("memory_id", 0),
            rag_root_ids=kwargs.get("rag_root_ids", []),
            tool_ids=kwargs.get("tool_ids", []),
            default_model_id=kwargs.get("default_model_id", kwargs.get("default_llm_id")),
            active_model_id=kwargs.get("active_model_id"),
            workspace_root=str(kwargs.get("workspace_root", "")),
            knowledge_root=str(kwargs.get("knowledge_root", "")),
            metadata=kwargs.get("metadata", {}),
        )
        agent_id = self._agent_repo.create(agent)
        created = replace(agent, id=agent_id)
        if not str(created.workspace_root).strip():
            created = replace(created, workspace_root=str(resolve_agent_workspace_root(created)))
            self._agent_repo.update(created)
        return created

    def clone_agent(self, source_agent_id: int, name: str, **kwargs) -> Agent:
        """Clone an existing agent into a new agent record."""
        source_agent = self._agent_repo.get(source_agent_id)
        if source_agent is None:
            raise ValueError(f"Agent not found: {source_agent_id}")
        if source_agent.owner_user_id is None:
            raise ValueError(f"Source agent {source_agent_id} has no owner_user_id.")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Agent name cannot be empty.")

        existing = self._agent_repo.get_by_name(clean_name)
        if existing:
            raise ValueError(f"Agent already exists: {clean_name}")

        prompt_id = kwargs.get("prompt_id")
        if prompt_id is None:
            if self._prompt_repo is not None and source_agent.prompt_id is not None:
                prompt = self._resolve_agent_prompt(source_agent)
                prompt_id = self._prompt_repo.create(replace(prompt))
            else:
                prompt_id = source_agent.prompt_id

        rag_root_ids = kwargs.get("rag_root_ids", source_agent.rag_root_ids)
        tool_ids = kwargs.get("tool_ids", source_agent.tool_ids)
        metadata = kwargs.get("metadata", source_agent.metadata)

        cloned = Agent(
            id=None,
            owner_user_id=kwargs.get("owner_user_id", source_agent.owner_user_id),
            owner_group_id=kwargs.get("owner_group_id", source_agent.owner_group_id),
            mode=kwargs.get("mode", source_agent.mode | 0o200),
            name=clean_name,
            prompt_id=prompt_id,
            system_prompt_id=kwargs.get("system_prompt_id", source_agent.system_prompt_id),
            memory_id=kwargs.get("memory_id", source_agent.memory_id),
            rag_root_ids=list(rag_root_ids or []),
            tool_ids=list(tool_ids or []),
            default_model_id=kwargs.get("default_model_id", source_agent.default_model_id),
            active_model_id=kwargs.get("active_model_id", source_agent.active_model_id),
            workspace_root=str(kwargs.get("workspace_root", "")),
            knowledge_root=str(kwargs.get("knowledge_root", source_agent.knowledge_root)),
            metadata=dict(metadata or {}),
        )
        agent_id = self._agent_repo.create(cloned)
        created = replace(cloned, id=agent_id)
        if not str(created.workspace_root).strip():
            created = replace(created, workspace_root=str(resolve_agent_workspace_root(created)))
            self._agent_repo.update(created)
        return created

    def update_agent(self, agent_id: int, **updates) -> Agent:
        """Update an existing agent."""
        agent = self._agent_repo.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent not found: {agent_id}")

        # Build updated agent
        updated = replace(
            agent,
            owner_user_id=updates.get("owner_user_id", agent.owner_user_id),
            owner_group_id=updates.get("owner_group_id", agent.owner_group_id),
            mode=updates.get("mode", agent.mode),
            name=updates.get("name", agent.name),
            prompt_id=updates.get("prompt_id", agent.prompt_id),
            system_prompt_id=updates.get("system_prompt_id", agent.system_prompt_id),
            memory_id=updates.get("memory_id", agent.memory_id),
            rag_root_ids=updates.get("rag_root_ids", agent.rag_root_ids),
            tool_ids=updates.get("tool_ids", agent.tool_ids),
            default_model_id=updates.get("default_model_id", updates.get("default_llm_id", agent.default_model_id)),
            active_model_id=updates.get("active_model_id", agent.active_model_id),
            workspace_root=updates.get("workspace_root", agent.workspace_root),
            knowledge_root=updates.get("knowledge_root", agent.knowledge_root),
            metadata=updates.get("metadata", agent.metadata),
            updated_at=utc_now(),
        )
        if not str(updated.workspace_root).strip():
            updated = replace(updated, workspace_root=str(resolve_agent_workspace_root(updated)))

        self._agent_repo.update(updated)
        return updated

    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent by ID."""
        return self._agent_repo.delete(agent_id)

    def get_agent(self, agent_id: int) -> Agent | None:
        """Get an agent by ID."""
        return self._agent_repo.get(agent_id)

    def list_agents(self) -> list[Agent]:
        """List all agents."""
        return self._agent_repo.list_all()

    def _resolve_agent_prompt(self, agent: Agent) -> AgentPrompt:
        if agent.prompt_id is not None and self._prompt_repo is not None:
            prompt = self._prompt_repo.get(agent.prompt_id)
            if prompt is not None:
                return prompt
        return default_agent_prompt()


_PROMPT_FIELDS = {
    "personality",
    "skills",
    "purpose",
    "backstory",
    "communication_style",
    "operating_principles",
    "autonomy_level",
    "decision_making_style",
    "memory_policy",
    "domain_priorities",
    "relationship_to_user",
    "tool_use_policy",
    "capability_boundaries",
    "output_preferences",
    "safety_ethics",
    "selfhood_truthfulness",
    "conflict_resolution_rules",
    "use_raw_prompt_override",
    "raw_prompt_override",
}
