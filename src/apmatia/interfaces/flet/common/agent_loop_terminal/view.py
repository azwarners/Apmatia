"""Flet view for the shared Agent Loop terminal."""

from __future__ import annotations

from typing import Any

import flet as ft

from .controller import AgentLoopTerminalController
from . import theme


VISIBLE_EVENT_TYPES = frozenset(
    {
        "user_message",
        "assistant_message",
        "tool_requested",
        "tool_awaiting_approval",
        "tool_result",
        "tool_failed",
        "tool_completed",
        "task_stopped",
        "task_failed",
        "execution_limit_reached",
        "task_archived",
    }
)


class AgentLoopTerminalView:
    def __init__(self, controller: AgentLoopTerminalController):
        self.controller = controller
        self.message = ft.TextField(label="Message", multiline=True, min_lines=2, expand=True)
        self.title = ft.TextField(label="New task title", value="Assistant task")
        self.feed = ft.ListView(expand=True, spacing=8, auto_scroll=True)
        self.container = ft.Container(bgcolor=theme.BACKGROUND, expand=True, padding=16)
        self._confirm_new_task = False
        controller._on_change = self.refresh
        self.refresh()

    def refresh(self) -> None:
        state = self.controller.state
        self.feed.controls = [
            self._event_card(event)
            for event in state.ordered_events
            if event.get("event_type") in VISIBLE_EVENT_TYPES
        ]
        agent_options = [ft.DropdownOption(key=str(agent.get("id")), text=str(agent.get("name") or agent.get("id"))) for agent in state.agents]
        selector = ft.Dropdown(label="Agent", options=agent_options, value=str(state.selected_agent_id) if state.selected_agent_id else None, on_select=lambda event: self.controller.select_agent(int(event.control.value)))
        task_options = [ft.DropdownOption(key=str(task.get("id")), text=str(task.get("title") or task.get("id"))) for task in state.tasks]
        task_selector = ft.Dropdown(label="Task", options=task_options, value=state.selected_task_id, on_select=lambda event: self.controller.select_task(str(event.control.value)))
        controls: list[ft.Control] = [ft.Text("Agent Loop Terminal", size=24, weight=ft.FontWeight.BOLD, color=theme.GREEN), selector, task_selector]
        new_task_label = "Confirm New Task" if self._confirm_new_task else "New Task"
        controls.append(ft.Row([self.title, ft.Button(new_task_label, on_click=lambda _event: self._new_task())]))
        controls.append(ft.Text(f"Status: {state.status}", color=theme.MUTED_GREEN))
        if state.pending_approval:
            pending = state.pending_approval
            controls.append(ft.Card(content=ft.Container(content=ft.Column([
                ft.Text(f"Approval required: {pending.get('tool_name', '')}", color=theme.WARNING),
                ft.Text(str(pending.get("description") or ""), color=theme.TEXT),
                ft.Text(f"Arguments: {pending.get('tool_call', {}).get('arguments', {})}"),
                ft.Text(f"Read-only: {pending.get('read_only', True)}"),
                ft.Row([ft.Button("Approve", on_click=lambda _event: self.controller.decide("approve")), ft.Button("Deny", on_click=lambda _event: self.controller.decide("deny"))]),
            ]), padding=12)))
        controls.append(self.feed)
        controls.append(ft.Row([self.message, ft.Button("Send", disabled=not state.send_enabled, on_click=lambda _event: self._send())]))
        controls.append(ft.Row([ft.Button("Copy", on_click=lambda _event: self.controller.copy_transcript()), ft.Button("Stop", disabled=state.status not in {"running", "awaiting_approval"}, on_click=lambda _event: self.controller.stop()), ft.Button("Archive", disabled=state.status not in {"idle", "stopped", "failed"}, on_click=lambda _event: self.controller.archive())]))
        if state.request_error:
            controls.append(ft.Text(state.request_error, color=theme.ERROR))
        self.container.content = ft.Column(controls=controls, expand=True)
        update = getattr(self.container, "update", None)
        if callable(update):
            try:
                update()
            except (AssertionError, RuntimeError):
                # Flet controls are not mounted during construction and unit tests.
                pass

    def _send(self) -> None:
        text = self.message.value
        self.message.value = ""
        self.controller.send(text)

    def _new_task(self) -> None:
        if not self._confirm_new_task:
            self._confirm_new_task = True
            self.refresh()
            return
        self._confirm_new_task = False
        self.controller.create_task(self.title.value)

    @staticmethod
    def _event_card(event: dict[str, Any]) -> ft.Control:
        event_type = str(event.get("event_type") or "event")
        payload = event.get("payload") or {}
        lines: list[str]
        if event_type == "tool_requested":
            arguments = payload.get("arguments") or payload.get("diagnostic") or {}
            lines = [
                f"Tool: {payload.get('tool_name') or 'unknown'}",
                f"Arguments: {arguments}",
            ]
        elif event_type in {"tool_result", "tool_failed", "tool_completed"}:
            lines = [
                f"Tool: {payload.get('tool_name') or 'unknown'}",
                f"Arguments: {payload.get('arguments') or payload.get('diagnostic') or {}}",
                f"Status: {payload.get('status') or ('failed' if event_type == 'tool_failed' else 'completed')}",
            ]
            if payload.get("output") is not None:
                lines.append(f"Output: {payload['output']}")
            if payload.get("error"):
                lines.append(f"Error: {payload['error']}")
        elif event_type == "tool_awaiting_approval":
            tool_call = payload.get("tool_call") or {}
            arguments = payload.get("arguments") or tool_call.get("arguments") or {}
            lines = [
                f"Tool: {payload.get('tool_name') or tool_call.get('tool_name') or 'unknown'}",
                f"Description: {payload.get('description') or ''}",
                f"Arguments: {arguments}",
                f"Read-only: {payload.get('read_only', True)}",
            ]
        else:
            text = payload.get("text") or payload.get("final_text") or payload.get("error") or ""
            lines = [str(text)]
        controls = [ft.Text(event_type.replace("_", " ").title(), color=theme.GREEN)]
        controls.extend(ft.Text(line, color=theme.TEXT) for line in lines)
        return ft.Container(content=ft.Column(controls), bgcolor=theme.PANEL, padding=10, border_radius=6)


def build_agent_loop_terminal(page: ft.Page, api: Any) -> ft.Control:
    controller = AgentLoopTerminalController(page, api)
    view = AgentLoopTerminalView(controller)
    controller.load_agents()
    return view.container
