from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .models import (
    AgentLoopTask,
    CancellationToken,
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


class AgentLoopTaskRepository(Protocol):
    def get(self, task_id: str) -> AgentLoopTask | None:
        raise NotImplementedError

    def save(self, task: AgentLoopTask) -> None:
        raise NotImplementedError

    def append_event(self, task_id: str, event) -> None:
        raise NotImplementedError

    def list_all(self) -> Sequence[AgentLoopTask]:
        raise NotImplementedError
