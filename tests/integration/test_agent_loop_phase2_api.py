from __future__ import annotations

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apmatia.api.http.app import create_app
from apmatia.modules.agent_loops.models import CancellationToken, ModelRequest, ModelResponse, ToolDefinition, ToolResult
from apmatia.modules.agent_loops.service import AgentLoopRuntime
from apmatia.modules.agent_loops.sqlite_repositories import SQLiteLoopTaskBundle


class _Phase2Model:
    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        del cancellation
        latest_user_text = ""
        for event in reversed(request.prior_events):
            if event.event_type.value == "user_message":
                latest_user_text = str(event.payload.get("text") or "")
                break
        if "approval" in latest_user_text.lower() and not request.tool_results:
            from apmatia.modules.agent_loops.models import ToolRequest

            return ModelResponse(
                tool_requests=(
                    ToolRequest(
                        tool_name="phase2_confirm",
                        arguments={"message": "confirm me"},
                        call_id=f"phase2_{uuid4().hex}",
                    ),
                )
            )
        return ModelResponse(final_text="Phase 2 deterministic response")


class _Phase2Tools:
    def __init__(self) -> None:
        self.approved_calls = 0

    def list_tools(self, context):  # type: ignore[no-untyped-def]
        return (
            ToolDefinition(
                name="phase2_confirm",
                description="Ask for confirmation.",
                metadata={"read_only": False},
            ),
        )

    def execute(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="pending_confirmation",
            metadata={"tool_id": 9001, "requester_agent_id": context.task.agent_id},
        )

    def execute_approved(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        self.approved_calls += 1
        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="success",
            output={"approved": True},
        )


@pytest.fixture
def phase2_api(tmp_path, monkeypatch):
    from apmatia.api.http.routes import shared
    from apmatia.modules.agent_loops import service as service_module

    class _DevelopmentRegistry:
        def list_modules(self, *, include_development: bool = False):
            del include_development
            return [type("Module", (), {"module_id": "agent_loops"})()]

    monkeypatch.setattr(shared, "get_application_registry", lambda: _DevelopmentRegistry())

    client = TestClient(create_app())
    username = f"phase2_{uuid4().hex[:12]}"
    registration = client.post(
        "/api/auth/register",
        json={"username": username, "password": "phase2-password"},
    )
    assert registration.status_code == 200, registration.text

    agent_response = client.post("/api/agents", json={"name": "Phase 2 Assistant"})
    assert agent_response.status_code == 200, agent_response.text
    agent_id = int(agent_response.json()["id"])

    database_path = tmp_path / "loop_tasks.db"
    tools = _Phase2Tools()
    model = _Phase2Model()
    runtime = AgentLoopRuntime(
        repository=SQLiteLoopTaskBundle(database_path).tasks,
        model_executor=model,
        tool_executor=tools,
        workspace_root=tmp_path / "workspace",
    )
    monkeypatch.setattr(service_module, "_runtime", runtime)
    return client, agent_id, database_path, model, tools, runtime


def _wait_for_status(client: TestClient, task_id: str, expected: str) -> dict:
    deadline = time.monotonic() + 3.0
    latest = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/agent-loops/tasks/{task_id}")
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest.get("status") == expected:
            return latest
        time.sleep(0.02)
    pytest.fail(f"Task {task_id} did not reach {expected}: {latest}")


def test_authenticated_phase2_flow_and_restart(phase2_api, monkeypatch):
    client, agent_id, database_path, model, tools, _runtime = phase2_api

    created = client.post(
        "/api/agent-loops/tasks",
        json={"agent_id": agent_id, "title": "Normal flow"},
    )
    assert created.status_code == 200, created.text
    normal_task_id = created.json()["id"]
    sent = client.post(
        f"/api/agent-loops/tasks/{normal_task_id}/messages",
        json={"text": "hello"},
    )
    assert sent.status_code == 200, sent.text
    normal = _wait_for_status(client, normal_task_id, "idle")
    assert [event["sequence"] for event in normal["events"]] == sorted(
        event["sequence"] for event in normal["events"]
    )
    assert any(event["event_type"] == "assistant_message" for event in normal["events"])

    approval_task = client.post(
        "/api/agent-loops/tasks",
        json={"agent_id": agent_id, "title": "Approval flow"},
    ).json()["id"]
    assert client.post(
        f"/api/agent-loops/tasks/{approval_task}/messages",
        json={"text": "please use approval"},
    ).status_code == 200
    awaiting = _wait_for_status(client, approval_task, "awaiting_approval")
    pending_call = awaiting["pending_tool_call"]
    assert pending_call["tool_id"] == 9001
    approval_event = next(
        event for event in awaiting["events"] if event["event_type"] == "tool_awaiting_approval"
    )
    assert approval_event["payload"]["description"] == "Ask for confirmation."
    assert approval_event["payload"]["read_only"] is False

    from apmatia.modules.agent_loops import service as service_module

    restarted = AgentLoopRuntime(
        repository=SQLiteLoopTaskBundle(database_path).tasks,
        model_executor=model,
        tool_executor=tools,
        workspace_root=database_path.parent / "workspace",
    )
    monkeypatch.setattr(service_module, "_runtime", restarted)
    restored = client.get(f"/api/agent-loops/tasks/{approval_task}").json()
    assert restored["pending_tool_call"] == pending_call

    approved = client.post(
        f"/api/agent-loops/tasks/{approval_task}/approval",
        json={"decision": "approve"},
    )
    assert approved.status_code == 200, approved.text
    completed = _wait_for_status(client, approval_task, "idle")
    assert tools.approved_calls == 1
    assert any(event["event_type"] == "assistant_message" for event in completed["events"])

    denied_task = client.post(
        "/api/agent-loops/tasks",
        json={"agent_id": agent_id, "title": "Deny flow"},
    ).json()["id"]
    assert client.post(
        f"/api/agent-loops/tasks/{denied_task}/messages",
        json={"text": "please use approval"},
    ).status_code == 200
    _wait_for_status(client, denied_task, "awaiting_approval")
    denied = client.post(
        f"/api/agent-loops/tasks/{denied_task}/approval",
        json={"decision": "deny"},
    )
    assert denied.status_code == 200, denied.text
    denied_done = _wait_for_status(client, denied_task, "idle")
    assert tools.approved_calls == 1
    assert any(
        event["event_type"] == "tool_failed" and event["payload"]["status"] == "denied"
        for event in denied_done["events"]
    )

    stopped_task = client.post(
        "/api/agent-loops/tasks",
        json={"agent_id": agent_id, "title": "Stop flow"},
    ).json()["id"]
    assert client.post(
        f"/api/agent-loops/tasks/{stopped_task}/messages",
        json={"text": "please use approval"},
    ).status_code == 200
    _wait_for_status(client, stopped_task, "awaiting_approval")
    stopped = client.post(f"/api/agent-loops/tasks/{stopped_task}/stop")
    assert stopped.status_code == 200, stopped.text
    assert _wait_for_status(client, stopped_task, "stopped")["status"] == "stopped"

    archived = client.post(f"/api/agent-loops/tasks/{normal_task_id}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
