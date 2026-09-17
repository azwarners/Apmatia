from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from apmatia.api.http.routes import agent_loop_routes as routes
from apmatia.api.internal import agent_loops as internal_agent_loops


def _request() -> object:
    return SimpleNamespace()


def test_conversation_create_payload_rejects_tool_input() -> None:
    with pytest.raises(ValueError):
        routes.ConversationTaskCreatePayload(agent_id=7, tools=[])


def test_get_task_returns_ordered_events_for_authorized_user() -> None:
    session = SimpleNamespace(user_id=42)
    task = {
        "id": "loop-1",
        "owner_user_id": 42,
        "owner_group_id": None,
        "events": [{"sequence": 1}, {"sequence": 2}],
    }
    with patch.object(routes, "require_session", return_value=session), patch.object(
        routes, "member_group_ids", return_value=set()
    ), patch.object(routes, "get_conversation_task", return_value=task):
        result = routes.get_task(_request(), "loop-1")
    assert result["events"] == [{"sequence": 1}, {"sequence": 2}]


def test_get_task_maps_access_denial_to_forbidden() -> None:
    session = SimpleNamespace(user_id=42)
    with patch.object(routes, "require_session", return_value=session), patch.object(
        routes, "member_group_ids", return_value=set()
    ), patch.object(
        routes,
        "get_conversation_task",
        side_effect=routes.LoopTaskAccessError("denied"),
    ):
        with pytest.raises(HTTPException) as error:
            routes.get_task(_request(), "loop-1")
    assert error.value.status_code == 403


def test_send_message_maps_active_run_to_conflict() -> None:
    session = SimpleNamespace(user_id=42)
    payload = routes.ConversationMessagePayload(text="hello")
    with patch.object(routes, "require_session", return_value=session), patch.object(
        routes, "member_group_ids", return_value=set()
    ), patch.object(
        routes,
        "submit_conversation_message",
        side_effect=RuntimeError("Task is not idle: running"),
    ):
        with pytest.raises(HTTPException) as error:
            routes.send_message(_request(), payload, "loop-1")
    assert error.value.status_code == 409


def test_approval_payload_accepts_only_approve_or_deny() -> None:
    assert routes.ConversationApprovalPayload(decision="approve").decision == "approve"
    with pytest.raises(ValueError):
        routes.ConversationApprovalPayload(decision="later")


def test_legacy_tasks_are_hidden_from_conversation_listing() -> None:
    agent = SimpleNamespace(owner_user_id=42, owner_group_id=None)
    runner = SimpleNamespace(
        list_tasks=lambda **_kwargs: [
            {"id": "legacy", "chat_mode": "single", "owner_user_id": 42},
            {"id": "conversation", "chat_mode": "conversation", "owner_user_id": 42},
        ]
    )
    with patch.object(internal_agent_loops, "get_agent_manager", return_value=SimpleNamespace(get_agent=lambda _id: agent)), patch.object(
        internal_agent_loops, "get_agent_loop_runner", return_value=runner
    ):
        result = internal_agent_loops.list_conversation_tasks(
            user_id=42, group_ids=set(), agent_id=7
        )
    assert [task["id"] for task in result] == ["conversation"]


def test_legacy_task_cannot_be_read_or_mutated_by_conversation_operations() -> None:
    runner = SimpleNamespace(
        get_task=lambda _task_id: {
            "id": "legacy",
            "chat_mode": "single",
            "owner_user_id": 42,
        }
    )
    with patch.object(internal_agent_loops, "get_agent_loop_runner", return_value=runner):
        with pytest.raises(KeyError):
            internal_agent_loops.get_conversation_task(
                task_id="legacy", user_id=42, group_ids=set()
            )
        with pytest.raises(KeyError):
            internal_agent_loops.submit_conversation_message(
                task_id="legacy", text="no", user_id=42, group_ids=set()
            )
