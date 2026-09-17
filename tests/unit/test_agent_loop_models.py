from __future__ import annotations

import pytest

from apmatia.modules.agent_loops.models import (
    AgentLoopTask,
    LoopEvent,
    LoopEventType,
    TaskStatus,
    ToolRequest,
)


@pytest.mark.parametrize("status", list(TaskStatus))
def test_task_status_values_round_trip(status: TaskStatus):
    task = AgentLoopTask(id="loop_model_status", status=status)

    restored = AgentLoopTask.from_dict(task.to_dict())

    assert restored.status is status


@pytest.mark.parametrize("event_type", list(LoopEventType))
def test_loop_event_values_and_payload_round_trip(event_type: LoopEventType):
    event = LoopEvent(
        event_type=event_type,
        task_id="loop_model_events",
        payload={"text": "hello", "arguments": {"value": 1}},
        sequence=3,
    )

    restored = LoopEvent.from_dict(event.to_dict())

    assert restored.event_type is event_type
    assert restored.payload == event.payload
    assert restored.sequence == 3


def test_task_persists_sequence_and_one_pending_tool_call():
    pending_call = ToolRequest(
        tool_name="calendar_write",
        arguments={"title": "Review plan"},
        call_id="call_1",
    ).to_dict()
    task = AgentLoopTask(
        id="loop_pending",
        status=TaskStatus.AWAITING_APPROVAL,
        next_event_sequence=8,
        pending_tool_call=pending_call,
    )

    restored = AgentLoopTask.from_dict(task.to_dict())

    assert restored.status is TaskStatus.AWAITING_APPROVAL
    assert restored.next_event_sequence == 8
    assert restored.pending_tool_call == pending_call


def test_unknown_legacy_fields_and_values_do_not_make_task_unreadable():
    restored = AgentLoopTask.from_dict(
        {
            "id": "legacy_task",
            "status": "status_added_by_newer_runtime",
            "future_field": {"ignored": True},
            "events": [
                {
                    "event_type": "event_added_by_newer_runtime",
                    "task_id": "legacy_task",
                    "payload": {"text": "still readable"},
                }
            ],
        }
    )

    assert restored.id == "legacy_task"
    assert restored.status is TaskStatus.DRAFT
    assert len(restored.events) == 1
    assert restored.events[0].event_type is LoopEventType.MODEL_ACTIVITY
