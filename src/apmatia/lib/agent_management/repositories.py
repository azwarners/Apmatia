from __future__ import annotations

from typing import Protocol

from .models import Agent


class AgentRepository(Protocol):
    def create(self, agent: Agent) -> int:
        """Persist a new agent and return its ID."""
        raise NotImplementedError

    def get(self, agent_id: int) -> Agent | None:
        """Return an agent by ID, or None if not found."""
        raise NotImplementedError

    def get_by_name(self, name: str) -> Agent | None:
        """Return an agent by name, or None if not found."""
        raise NotImplementedError

    def list_all(self) -> list[Agent]:
        """Return all agents."""
        raise NotImplementedError

    def update(self, agent: Agent) -> None:
        """Persist an existing agent."""
        raise NotImplementedError

    def delete(self, agent_id: int) -> bool:
        """Delete an agent by ID. Return True if a record was removed."""
        raise NotImplementedError
