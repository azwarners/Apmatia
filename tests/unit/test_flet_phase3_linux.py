"""Phase 3.2 Linux host integration tests."""

from __future__ import annotations

from unittest.mock import Mock

import flet as ft

from apmatia.interfaces.flet.linux.shell import ApmatiaShell


class FakePage:
    def __init__(self) -> None:
        self.controls: list[ft.Control] = []
        self.route = "/"
        self.run_task = Mock()

    def add(self, *controls: ft.Control) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        pass


def test_linux_shell_routes_agent_loops_to_shared_terminal() -> None:
    page = FakePage()
    api = Mock()
    api.list_modules.return_value = [
        {
            "module_id": "agent_loops",
            "name": "Agent Loops",
            "views": [{"view_id": "agent_loops.loops.view", "name": "Agent Loops"}],
        }
    ]
    api.list_agents.return_value = [{"id": 7, "name": "Executive Assistant"}]
    api.list_agent_loop_tasks.return_value = [{"id": "task-1", "title": "Inbox", "status": "idle"}]

    shell = ApmatiaShell(page, api)
    shell._state.set_authenticated({"user_id": 1, "username": "nick"})
    page.route = "/view/agent_loops.loops.view"
    shell.render_route()

    assert shell._terminal_controller is not None
    assert shell._terminal_controller.state.selected_agent_id == 7
    assert shell._terminal_controller.state.tasks[0]["id"] == "task-1"
    api.get_module_view_document.assert_not_called()


def test_linux_terminal_drives_task_transcript_and_approval_through_api() -> None:
    page = FakePage()
    api = Mock()
    api.list_modules.return_value = [{"module_id": "agent_loops", "views": [{"view_id": "agent_loops.loops.view"}]}]
    api.list_agents.return_value = [{"id": 7, "name": "Assistant"}]
    api.list_agent_loop_tasks.return_value = [{"id": "task-1", "title": "Inbox", "status": "idle"}]
    api.get_agent_loop_task.return_value = {
        "id": "task-1",
        "status": "idle",
        "events": [{"sequence": 1, "event_type": "assistant_message", "payload": {"text": "Ready."}}],
    }
    api.send_agent_loop_message.return_value = {
        "id": "task-1",
        "status": "awaiting_approval",
        "pending_tool_call": {
            "tool_name": "calendar.create",
            "description": "Create an event",
            "read_only": False,
        },
        "events": [
            {"sequence": 1, "event_type": "assistant_message", "payload": {"text": "Ready."}},
            {
                "sequence": 2,
                "event_type": "tool_awaiting_approval",
                "payload": {
                    "tool_name": "calendar.create",
                    "description": "Create an event",
                    "read_only": False,
                },
            },
        ],
    }
    api.decide_agent_loop_approval.return_value = {
        "id": "task-1",
        "status": "idle",
        "events": [
            {"sequence": 1, "event_type": "assistant_message", "payload": {"text": "Ready."}},
            {"sequence": 2, "event_type": "tool_result", "payload": {"output": "Created."}},
            {"sequence": 3, "event_type": "assistant_message", "payload": {"text": "Done."}},
        ],
    }

    shell = ApmatiaShell(page, api)
    shell._state.set_authenticated({"user_id": 1, "username": "nick"})
    page.route = "/view/agent_loops.loops.view"
    shell.render_route()
    controller = shell._terminal_controller
    assert controller is not None

    controller.select_task("task-1")
    controller.send("Please create the event")
    assert controller.state.status == "awaiting_approval"
    assert controller.state.pending_approval["description"] == "Create an event"

    controller.decide("approve")
    assert controller.state.status == "idle"
    assert controller.state.ordered_events[-1]["payload"]["text"] == "Done."
    api.send_agent_loop_message.assert_called_once_with("task-1", "Please create the event")
    api.decide_agent_loop_approval.assert_called_once_with("task-1", "approve")


def test_linux_route_change_cancels_terminal_polling_without_rebuilding_window() -> None:
    page = FakePage()
    api = Mock()
    api.list_modules.return_value = [{"module_id": "agent_loops", "views": [{"view_id": "agent_loops.loops.view"}]}]
    api.list_agents.return_value = [{"id": 7, "name": "Assistant"}]
    api.list_agent_loop_tasks.return_value = [{"id": "task-1", "title": "Inbox", "status": "running"}]

    shell = ApmatiaShell(page, api)
    shell._state.set_authenticated({"user_id": 1, "username": "nick"})
    page.route = "/view/agent_loops.loops.view"
    shell.render_route()
    controller = shell._terminal_controller
    assert controller is not None
    poll = Mock(done=Mock(return_value=False))
    controller._poll_task = poll
    original_route = page.route

    page.route = "/"
    shell.render_route()

    poll.cancel.assert_called_once_with()
    assert page.route == "/"
    assert page.route != original_route
