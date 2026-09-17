"""Controller for the shared Agent Loop terminal."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any, Callable

import flet as ft

from ..api_client import ApmatiaApiClient
from ..errors import AdapterError
from .reducer import AgentLoopTerminalState, apply_task_snapshot, reduce_event, request_failed


class AgentLoopTerminalController:
    ACTIVE_STATUSES = frozenset({"queued", "running", "stopping", "awaiting_approval"})

    def __init__(self, page: ft.Page, api: ApmatiaApiClient, *, on_change: Callable[[], None] | None = None):
        self.page = page
        self.api = api
        self.state = AgentLoopTerminalState()
        self._on_change = on_change or (lambda: self.page.update())
        self._poll_task: Any = None
        self._poll_key: tuple[int | None, str | None] = (None, None)

    def _changed(self) -> None:
        self._on_change()

    def load_agents(self) -> None:
        try:
            agents = tuple(self.api.list_agents())
            selected = self.state.selected_agent_id or (int(agents[0]["id"]) if agents else None)
            self.state = replace(self.state, agents=agents, selected_agent_id=selected)
            self.load_tasks(selected)
        except (AdapterError, ValueError, KeyError) as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def load_tasks(self, agent_id: int | None = None) -> None:
        agent_id = agent_id if agent_id is not None else self.state.selected_agent_id
        if agent_id is None:
            return
        try:
            tasks = tuple(self.api.list_agent_loop_tasks(agent_id))
            self.state = replace(self.state, tasks=tasks, selected_agent_id=agent_id)
            self._changed()
        except AdapterError as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def select_agent(self, agent_id: int) -> None:
        self.stop_polling()
        self.state = replace(self.state, selected_agent_id=int(agent_id), selected_task_id=None, events={})
        self.load_tasks(int(agent_id))

    def select_task(self, task_id: str) -> None:
        self.stop_polling()
        try:
            self.state = apply_task_snapshot(self.state, self.api.get_agent_loop_task(task_id))
            self._poll_key = (self.state.selected_agent_id, task_id)
            self._changed()
            self._ensure_polling()
        except AdapterError as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def create_task(self, title: str = "") -> None:
        if self.state.selected_agent_id is None:
            return
        try:
            current_task_id = self.state.selected_task_id
            if current_task_id and self.state.status != "archived":
                if self.state.status not in {"idle", "stopped", "failed", "cancelled", "limit_reached"}:
                    self.state = request_failed(
                        self.state,
                        "Stop or finish the current task before creating a new one.",
                    )
                    self._changed()
                    return
                archived = self.api.archive_agent_loop_task(current_task_id)
                self.state = apply_task_snapshot(self.state, archived)
            task = self.api.create_agent_loop_task(self.state.selected_agent_id, title)
            self.state = apply_task_snapshot(self.state, task)
            self._poll_key = (self.state.selected_agent_id, self.state.selected_task_id)
            self._changed()
        except AdapterError as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def send(self, text: str) -> None:
        if not self.state.send_enabled or not str(text).strip():
            return
        try:
            self.state = apply_task_snapshot(self.state, self.api.send_agent_loop_message(self.state.selected_task_id or "", text))
            self._changed()
            self._ensure_polling()
        except AdapterError as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def stop(self) -> None:
        self._mutate_task(self.api.stop_agent_loop_task)

    def archive(self) -> None:
        self._mutate_task(self.api.archive_agent_loop_task)

    def decide(self, decision: str) -> None:
        self._mutate_task(lambda task_id: self.api.decide_agent_loop_approval(task_id, decision))

    def copy_transcript(self) -> str:
        value = "\n".join(
            str(
                event.get("payload", {}).get("text")
                or event.get("payload", {}).get("final_text")
                or event.get("payload", {}).get("output")
                or event.get("payload", {}).get("error")
                or ""
            )
            for event in self.state.ordered_events
        ).strip()
        set_clipboard = getattr(self.page, "set_clipboard", None)
        if callable(set_clipboard):
            set_clipboard(value)
        return value

    def _mutate_task(self, operation: Callable[[str], dict[str, Any]]) -> None:
        if not self.state.selected_task_id:
            return
        try:
            self.state = apply_task_snapshot(self.state, operation(self.state.selected_task_id))
            self._changed()
            self._ensure_polling()
        except AdapterError as error:
            self.state = request_failed(self.state, str(error))
            self._changed()

    def _ensure_polling(self) -> None:
        if self.state.status in self.ACTIVE_STATUSES and (self._poll_task is None or self._poll_task.done()):
            self._poll_task = self.page.run_task(self._poll_loop)

    def stop_polling(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
        self._poll_task = None

    async def _poll_loop(self) -> None:
        while self._poll_key == (self.state.selected_agent_id, self.state.selected_task_id) and self.state.status in self.ACTIVE_STATUSES:
            await asyncio.sleep(1.0)
            if self._poll_key != (self.state.selected_agent_id, self.state.selected_task_id):
                return
            try:
                previous = self._semantic_snapshot(self.state)
                self.state = apply_task_snapshot(self.state, self.api.get_agent_loop_task(self.state.selected_task_id or ""))
                if self._semantic_snapshot(self.state) != previous:
                    self._changed()
            except AdapterError as error:
                self.state = request_failed(self.state, str(error))
                self._changed()
                return

    @staticmethod
    def _semantic_snapshot(state: AgentLoopTerminalState) -> tuple[Any, ...]:
        return (
            state.selected_task_id,
            state.status,
            state.pending_approval,
            tuple((sequence, event) for sequence, event in sorted(state.events.items())),
            state.request_error,
        )
