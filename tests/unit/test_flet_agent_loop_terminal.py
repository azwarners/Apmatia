"""Phase 3.1 tests for the shared Agent Loop terminal package."""

from __future__ import annotations

from dataclasses import replace
import asyncio
from unittest.mock import Mock, call

import flet as ft
import pytest

from apmatia.interfaces.flet.common.agent_loop_terminal.controller import AgentLoopTerminalController
from apmatia.interfaces.flet.common.agent_loop_terminal.dto import AgentLoopEventDto, AgentLoopTaskDto
from apmatia.interfaces.flet.common.agent_loop_terminal.reducer import (
    AgentLoopTerminalState,
    apply_task_snapshot,
    reduce_event,
    request_failed,
)
from apmatia.interfaces.flet.common.agent_loop_terminal.view import AgentLoopTerminalView
from apmatia.interfaces.flet.common.api_client import ApmatiaApiClient
from apmatia.interfaces.flet.common.errors import AdapterError


def _event(sequence: int, event_type: str, **payload: object) -> dict:
    return {"sequence": sequence, "event_type": event_type, "payload": payload}


def test_reducer_orders_events_and_deduplicates_sequences() -> None:
    state = AgentLoopTerminalState(selected_task_id="task-1")
    state = reduce_event(state, _event(2, "assistant_message", text="two"))
    state = reduce_event(state, _event(1, "user_message", text="one"))
    duplicate = reduce_event(state, _event(1, "user_message", text="replaced"))

    assert [event["sequence"] for event in state.ordered_events] == [1, 2]
    assert state.ordered_events[0]["payload"]["text"] == "one"
    assert duplicate is state


def test_reducer_tracks_approval_and_terminal_statuses() -> None:
    state = AgentLoopTerminalState(selected_task_id="task-1")
    state = reduce_event(state, _event(1, "tool_awaiting_approval", tool_name="calendar.create", read_only=False))
    assert state.status == "awaiting_approval"
    assert state.pending_approval == {"tool_name": "calendar.create", "read_only": False}

    state = reduce_event(state, _event(2, "task_stopped"))
    assert state.status == "stopped"
    assert state.pending_approval is None


def test_snapshot_rebuilds_event_state_and_request_errors_are_visible() -> None:
    state = AgentLoopTerminalState(request_error="old error")
    state = apply_task_snapshot(
        state,
        {"id": "task-9", "status": "running", "events": [_event(4, "task_started")]},
    )

    assert state.selected_task_id == "task-9"
    assert state.status == "running"
    assert state.ordered_events[0]["sequence"] == 4
    assert request_failed(state, "network down").request_error == "network down"


@pytest.mark.parametrize("continuation_status", ["running", "idle"])
def test_snapshot_status_clears_historic_approval_after_approve_or_deny(continuation_status: str) -> None:
    state = apply_task_snapshot(
        AgentLoopTerminalState(),
        {
            "id": "task-9",
            "status": continuation_status,
            "pending_tool_call": None,
            "events": [
                _event(
                    1,
                    "tool_awaiting_approval",
                    tool_name="calendar.create",
                    arguments={"title": "Review"},
                ),
                _event(2, "tool_result", tool_name="calendar.create", output="Created."),
            ],
        },
    )

    assert state.status == continuation_status
    assert state.pending_approval is None


def test_snapshot_enriches_live_minimal_pending_call_from_approval_event() -> None:
    state = apply_task_snapshot(
        AgentLoopTerminalState(),
        {
            "id": "task-approval",
            "status": "awaiting_approval",
            "pending_tool_call": {
                "tool_id": 17,
                "arguments": {"title": "Review"},
                "requester_agent_id": 7,
                "call_id": "call-17",
                "tool_name": "calendar.create",
            },
            "events": [
                _event(
                    4,
                    "tool_awaiting_approval",
                    tool_name="calendar.create",
                    call_id="call-17",
                    description="Create a calendar event",
                    read_only=False,
                    tool_call={"call_id": "call-17", "arguments": {"title": "Review"}},
                ),
            ],
        },
    )

    assert state.status == "awaiting_approval"
    assert state.pending_approval["description"] == "Create a calendar event"
    assert state.pending_approval["read_only"] is False


def test_dtos_extract_core_task_and_event_payloads() -> None:
    event = AgentLoopEventDto.from_dict(_event(3, "assistant_message", text="hello"))
    task = AgentLoopTaskDto.from_dict(
        {"id": "task-1", "status": "awaiting_approval", "events": [_event(3, "assistant_message", text="hello")]}
    )

    assert event.sequence == 3
    assert event.payload["text"] == "hello"
    assert task.task_id == "task-1"
    assert task.events == (event,)


def test_api_client_exposes_typed_agent_loop_operations() -> None:
    client = ApmatiaApiClient("http://core/api")
    client._request = Mock(side_effect=[
        {"items": [{"id": 7, "name": "Assistant"}]},
        [{"id": "task-1", "title": "Inbox"}],
        {"id": "task-2", "status": "idle"},
        {"id": "task-2", "status": "idle"},
        {"id": "task-2", "status": "running"},
        {"id": "task-2", "status": "stopped"},
        {"id": "task-2", "status": "archived"},
        {"id": "task-2", "status": "running"},
    ])

    assert client.list_agents()[0]["id"] == 7
    assert client.list_agent_loop_tasks(7)[0]["id"] == "task-1"
    client.create_agent_loop_task(7, "Inbox")
    client.get_agent_loop_task("task-2")
    client.send_agent_loop_message("task-2", "hello")
    client.stop_agent_loop_task("task-2")
    client.archive_agent_loop_task("task-2")
    client.decide_agent_loop_approval("task-2", "approve")

    calls = client._request.call_args_list
    assert calls[0].args == ("POST", "/module-commands/agents.list")
    assert calls[1].args == ("GET", "/agent-loops/tasks?agent_id=7")
    assert calls[2].kwargs["json"] == {"agent_id": 7, "title": "Inbox"}
    assert calls[-1].kwargs["json"] == {"decision": "approve"}

    with pytest.raises(ValueError):
        client.decide_agent_loop_approval("task-2", "maybe")


class FakePage:
    def __init__(self) -> None:
        self.clipboard = None
        self.run_task = Mock()

    def set_clipboard(self, value: str) -> None:
        self.clipboard = value

    def update(self) -> None:
        pass


def test_controller_disables_send_while_running_and_copies_transcript() -> None:
    page = FakePage()
    api = Mock()
    controller = AgentLoopTerminalController(page, api)
    controller.state = apply_task_snapshot(
        controller.state,
        {"id": "task-1", "status": "running", "events": [_event(1, "assistant_message", text="hello")]},
    )

    controller.send("should not send")
    assert not api.send_agent_loop_message.called
    assert controller.state.send_enabled is False
    assert controller.copy_transcript() == "hello"
    assert page.clipboard == "hello"


def test_controller_cancels_polling_on_selection_change() -> None:
    page = FakePage()
    api = Mock()
    controller = AgentLoopTerminalController(page, api)
    poll = Mock()
    poll.done.return_value = False
    controller._poll_task = poll

    controller.stop_polling()

    poll.cancel.assert_called_once_with()
    assert controller._poll_task is None


def test_selection_changes_cancel_the_existing_poll_for_task_and_agent() -> None:
    page = FakePage()
    api = Mock()
    api.get_agent_loop_task.return_value = {"id": "task-2", "status": "idle", "events": []}
    api.list_agent_loop_tasks.return_value = []
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(
        selected_agent_id=7,
        selected_task_id="task-1",
        status="running",
    )

    task_poll = Mock(done=Mock(return_value=False))
    controller._poll_task = task_poll
    controller.select_task("task-2")
    task_poll.cancel.assert_called_once_with()

    agent_poll = Mock(done=Mock(return_value=False))
    controller._poll_task = agent_poll
    controller.select_agent(8)
    agent_poll.cancel.assert_called_once_with()


def test_queued_send_starts_polling_immediately() -> None:
    page = FakePage()
    api = Mock()
    poll = Mock()
    poll.done.return_value = False
    page.run_task.return_value = poll
    api.send_agent_loop_message.return_value = {"id": "task-1", "status": "queued", "events": []}
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(selected_agent_id=7, selected_task_id="task-1", status="idle")

    controller.send("hello")

    page.run_task.assert_called_once_with(controller._poll_loop)
    assert controller.state.status == "queued"


def test_polling_continues_queued_to_running_and_stops_at_idle() -> None:
    page = FakePage()
    api = Mock()
    api.get_agent_loop_task.side_effect = [
        {"id": "task-1", "status": "running", "events": []},
        {"id": "task-1", "status": "idle", "events": []},
    ]
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(selected_agent_id=7, selected_task_id="task-1", status="queued")
    controller._poll_key = (7, "task-1")

    async def no_sleep(_seconds: float) -> None:
        return None

    original_sleep = asyncio.sleep
    asyncio.sleep = no_sleep
    try:
        asyncio.run(controller._poll_loop())
    finally:
        asyncio.sleep = original_sleep

    assert api.get_agent_loop_task.call_count == 2
    assert controller.state.status == "idle"


def test_polling_redraws_mounted_terminal_only_for_semantic_changes() -> None:
    page = FakePage()
    api = Mock()
    api.get_agent_loop_task.side_effect = [
        {"id": "task-1", "status": "queued", "events": []},
        {"id": "task-1", "status": "running", "events": [_event(1, "tool_requested", tool_name="lookup", arguments={"q": "x"})]},
        {"id": "task-1", "status": "idle", "events": [_event(1, "tool_requested", tool_name="lookup", arguments={"q": "x"})]},
    ]
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(selected_agent_id=7, selected_task_id="task-1", status="queued")
    controller._poll_key = (7, "task-1")
    view = AgentLoopTerminalView(controller)
    update = Mock()
    view.container.update = update

    async def no_sleep(_seconds: float) -> None:
        return None

    original_sleep = asyncio.sleep
    asyncio.sleep = no_sleep
    try:
        asyncio.run(controller._poll_loop())
    finally:
        asyncio.sleep = original_sleep

    # The first queued snapshot is unchanged; running and idle each change the feed/status.
    assert update.call_count == 2
    assert view.container.content is not None


def test_repeated_ensure_polling_starts_only_one_task() -> None:
    page = FakePage()
    api = Mock()
    poll = Mock(done=Mock(return_value=False))
    page.run_task.return_value = poll
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(selected_task_id="task-1", status="queued")

    controller._ensure_polling()
    controller._ensure_polling()

    page.run_task.assert_called_once_with(controller._poll_loop)


@pytest.mark.parametrize("status", ["idle", "stopped", "failed", "archived"])
def test_non_active_statuses_do_not_start_polling(status: str) -> None:
    page = FakePage()
    api = Mock()
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(selected_task_id="task-1", status=status)

    controller._ensure_polling()

    page.run_task.assert_not_called()


def test_new_task_archives_current_task_before_creating_replacement() -> None:
    page = FakePage()
    api = Mock()
    api.archive_agent_loop_task.return_value = {"id": "task-1", "status": "archived", "events": []}
    api.create_agent_loop_task.return_value = {"id": "task-2", "status": "idle", "events": []}
    controller = AgentLoopTerminalController(page, api)
    controller.state = apply_task_snapshot(
        controller.state,
        {"id": "task-1", "status": "idle", "events": []},
    )
    controller.state = replace(
        controller.state,
        agents=({"id": 7, "name": "Assistant"},),
        selected_agent_id=7,
    )

    controller.create_task("Replacement")

    api.archive_agent_loop_task.assert_called_once_with("task-1")
    api.create_agent_loop_task.assert_called_once_with(7, "Replacement")
    assert api.method_calls[:2] == [
        call.archive_agent_loop_task("task-1"),
        call.create_agent_loop_task(7, "Replacement"),
    ]
    assert controller.state.selected_task_id == "task-2"


def test_new_task_does_not_create_when_archiving_current_task_fails() -> None:
    page = FakePage()
    api = Mock()
    api.archive_agent_loop_task.side_effect = AdapterError("archive failed")
    controller = AgentLoopTerminalController(page, api)
    controller.state = AgentLoopTerminalState(
        selected_agent_id=7,
        selected_task_id="task-1",
        status="idle",
    )

    controller.create_task("Replacement")

    api.create_agent_loop_task.assert_not_called()
    assert controller.state.request_error == "archive failed"


def test_view_contains_terminal_controls_and_renders_event_text() -> None:
    page = FakePage()
    api = Mock()
    controller = AgentLoopTerminalController(page, api)
    controller.state = apply_task_snapshot(
        controller.state,
        {
            "id": "task-1",
            "status": "awaiting_approval",
            "pending_tool_call": {"tool_name": "calendar.create", "description": "Create an event", "read_only": False},
            "events": [_event(1, "tool_failed", error="failed")],
        },
    )
    view = AgentLoopTerminalView(controller)

    def text_fields(control: ft.Control) -> list[ft.TextField]:
        found = [control] if isinstance(control, ft.TextField) else []
        for child in getattr(control, "controls", []) or []:
            found.extend(text_fields(child))
        content = getattr(control, "content", None)
        if content is not None:
            found.extend(text_fields(content))
        return found

    labels = [control.label for control in text_fields(view.container)]
    rendered = view._event_card(_event(1, "tool_failed", error="failed"))

    assert "Message" in labels
    assert "New task title" in labels
    assert any("failed" in control.value for control in rendered.content.controls)
    assert view.container.content.controls


@pytest.mark.parametrize(
    ("event_type", "payload", "expected"),
    [
        ("user_message", {"text": "Hello"}, "Hello"),
        ("assistant_message", {"text": "Done"}, "Done"),
        ("tool_requested", {"tool_name": "calendar.create", "arguments": {"title": "Review"}}, "calendar.create"),
        ("tool_result", {"tool_name": "calendar.create", "status": "success", "output": "Created"}, "Created"),
        ("tool_failed", {"tool_name": "calendar.create", "status": "failed", "error": "Denied"}, "Denied"),
        (
            "tool_awaiting_approval",
            {"tool_name": "calendar.create", "description": "Create event", "arguments": {"title": "Review"}, "read_only": False},
            "Create event",
        ),
    ],
)
def test_event_renderer_shows_structured_tool_and_message_content(
    event_type: str, payload: dict[str, object], expected: str
) -> None:
    rendered = AgentLoopTerminalView._event_card(_event(1, event_type, **payload))
    values = [control.value for control in rendered.content.controls]

    assert any(expected in value for value in values)


def test_malformed_memory_create_failure_renders_recovered_arguments() -> None:
    rendered = AgentLoopTerminalView._event_card(
        _event(
            1,
            "tool_failed",
            tool_name="memory_create",
            arguments={"text": "remember this"},
            diagnostic=None,
            status="failed",
            error={"code": "INVALID_TOOL_REQUEST", "message": "MALFORMED_TOOL_CALL: unterminated tool call block."},
        )
    )
    values = [control.value for control in rendered.content.controls]

    assert any("Tool: memory_create" == value for value in values)
    assert any("Arguments: {'text': 'remember this'}" == value for value in values)


def test_terminal_acceptance_hides_streaming_trace_noise_and_protocol_markup() -> None:
    page = FakePage()
    api = Mock()
    controller = AgentLoopTerminalController(page, api)
    activity_events = [
        _event(sequence, "model_activity", text=f"stream fragment {sequence}")
        for sequence in range(1, 21)
    ]
    controller.state = apply_task_snapshot(
        controller.state,
        {
            "id": "task-streaming",
            "status": "idle",
            "events": [
                *activity_events,
                _event(21, "task_started"),
                _event(22, "model_turn_started"),
                _event(23, "user_message", text="Use the lookup tool."),
                _event(24, "tool_requested", tool_name="lookup", arguments={"query": "today"}),
                _event(25, "tool_result", tool_name="lookup", status="success", output="Found it."),
                _event(26, "model_turn_completed", final_text='<tool_call>{"name":"lookup"}'),
                _event(27, "assistant_message", text="Here is the result."),
                _event(28, "task_completed", final_text="Here is the result."),
            ],
        },
    )
    view = AgentLoopTerminalView(controller)

    rendered_types = [
        card.content.controls[0].value.lower().replace(" ", "_")
        for card in view.feed.controls
    ]
    rendered_text = "\n".join(
        text.value
        for card in view.feed.controls
        for text in card.content.controls
        if isinstance(text, ft.Text)
    )

    assert rendered_types == ["user_message", "tool_requested", "tool_result", "assistant_message"]
    assert "MODEL_ACTIVITY" not in rendered_text
    assert "model_turn" not in rendered_text
    assert "<tool_call>" not in rendered_text
