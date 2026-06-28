from __future__ import annotations

from typing import Protocol

from .models import Agent


class AgentService(Protocol):
    def create_agent(self, name: str, **kwargs) -> Agent:
        """Create and return an agent record."""
        raise NotImplementedError

    def clone_agent(self, source_agent_id: int, name: str, **kwargs) -> Agent:
        """Clone an existing agent into a new record."""
        raise NotImplementedError

    def update_agent(self, agent_id: int, **updates) -> Agent:
        """Update and return an agent record."""
        raise NotImplementedError

    def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent by ID. Return True if removed."""
        raise NotImplementedError

    def get_agent(self, agent_id: int) -> Agent | None:
        """Return an agent by ID, or None if not found."""
        raise NotImplementedError

    def list_agents(self) -> list[Agent]:
        """List all agents."""
        raise NotImplementedError
