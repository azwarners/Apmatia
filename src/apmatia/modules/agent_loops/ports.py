from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import (
    AgentLoopTask,
    CancellationToken,
    LoopEvent,
    ModelRequest,
    ModelResponse,
    ToolContext,
    ToolDefinition,
    ToolRequest,
    ToolResult,
)


class ModelExecutor(Protocol):
    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        raise NotImplementedError


class ToolExecutor(Protocol):
    def list_tools(self, context: ToolContext) -> Sequence[ToolDefinition]:
        raise NotImplementedError

    def execute(self, request: ToolRequest, context: ToolContext, cancellation: CancellationToken) -> ToolResult:
        raise NotImplementedError

    def execute_approved(
        self, request: ToolRequest, context: ToolContext, cancellation: CancellationToken
    ) -> ToolResult:
        """Execute a previously persisted call with confirmation granted."""
        raise NotImplementedError


class AgentLoopTaskRepository(Protocol):
    def create(self, task: AgentLoopTask) -> AgentLoopTask:
        """Persist and return a new task."""
        raise NotImplementedError

    def get(self, task_id: str) -> AgentLoopTask | None:
        raise NotImplementedError

    def update(self, task: AgentLoopTask) -> None:
        raise NotImplementedError

    def save(self, task: AgentLoopTask) -> None:
        """Legacy alias retained for file-backed task persistence."""
        raise NotImplementedError

    def list_tasks(
        self,
        *,
        agent_id: int | None = None,
        include_archived: bool = False,
    ) -> Sequence[AgentLoopTask]:
        raise NotImplementedError

    def list_all(self) -> Sequence[AgentLoopTask]:
        """Legacy listing method retained for existing runtimes/tests."""
        raise NotImplementedError

    def append_ordered_event(self, task_id: str, event: LoopEvent) -> LoopEvent:
        """Append an event with a repository-allocated sequence."""
        raise NotImplementedError

    def append_event(self, task_id: str, event: LoopEvent) -> None:
        """Legacy event append method retained for existing runtimes/tests."""
        raise NotImplementedError

    def list_ordered_events(self, task_id: str, *, after_sequence: int = 0) -> Sequence[LoopEvent]:
        raise NotImplementedError

    def reconcile_next_event_sequence(self, task_id: str) -> int:
        raise NotImplementedError
