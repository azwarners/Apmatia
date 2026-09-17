from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from threading import Event

import pytest

from apmatia.modules.agent_loops.executor import AgentLoopExecutor
from apmatia.modules.agent_loops.models import (
    AgentLoopExecutionRequest,
    AgentLoopTask,
    CancellationToken,
    ExecutionStatus,
    LoopEventType,
    ModelRequest,
    ModelResponse,
    TaskStatus,
    ToolDefinition,
    ToolRequest,
    ToolResult,
)
from apmatia.modules.agent_loops.repository import InMemoryAgentLoopTaskRepository
from apmatia.modules.agent_loops.service import AgentLoopRuntime
from apmatia.modules.agent_loops.sqlite_repositories import SQLiteLoopTaskBundle


class _Agent:
    id = 7
    name = "Executive Assistant"
    mode = 0
    active_model_id = None
    default_model_id = None
    owner_group_id = None
    workspace_root = ""


class _ConversationModel:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(final_text="Acknowledged")


class _TwoToolCycleModel:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        self.calls += 1
        if self.calls <= 2:
            return ModelResponse(
                tool_requests=(ToolRequest(tool_name="lookup", arguments={"step": self.calls}),)
            )
        return ModelResponse(final_text="Finished both lookups")


class _LookupTools:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def list_tools(self, context):  # type: ignore[no-untyped-def]
        return (
            ToolDefinition(
                name="lookup",
                description="Look up a value.",
                metadata={"read_only": False},
            ),
        )

    def execute(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.fail:
            return ToolResult(
                tool_name=request.tool_name,
                call_id=request.call_id,
                status="failed",
                error="lookup unavailable",
            )
        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="success",
            output={"step": self.calls},
        )


class _ApprovalTools:
    def __init__(self) -> None:
        self.approved_calls = []

    def list_tools(self, context):  # type: ignore[no-untyped-def]
        return (
            ToolDefinition(
                name="lookup",
                description="Look up a value.",
                metadata={"read_only": False},
            ),
        )

    def execute(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="pending_confirmation",
            metadata={"tool_id": 17, "requester_agent_id": 7},
        )

    def execute_approved(self, request, context, cancellation):  # type: ignore[no-untyped-def]
        self.approved_calls.append(request)
        return ToolResult(
            tool_name=request.tool_name,
            call_id=request.call_id,
            status="success",
            output={"approved": True},
        )


def _conversation_task() -> AgentLoopTask:
    return AgentLoopTask(
        id="conversation_1",
        owner_user_id=7,
        agent_id=7,
        contact_kind="agent",
        contact_id="7",
        chat_mode="conversation",
        status=TaskStatus.IDLE,
        max_model_turns=5,
        max_tool_calls=5,
    )


def test_runtime_creates_conversation_and_persists_user_and_assistant_events(monkeypatch, tmp_path: Path):
    from apmatia.modules.agent_loops import service as service_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: type("Manager", (), {"get_agent": lambda self, _: _Agent()})())
    model = _ConversationModel()
    runtime = AgentLoopRuntime(
        repository=InMemoryAgentLoopTaskRepository(),
        model_executor=model,
        tool_executor=_LookupTools(),
        workspace_root=tmp_path,
    )

    created = runtime.create_task(agent_id=7, owner_user_id=7, title="Assistant chat")
    submitted = runtime.submit_message(created["id"], "What should I do first?")

    assert submitted["id"] == created["id"]
    assert runtime.wait_for_task(created["id"], timeout=2.0)
    task = runtime.get_task(created["id"])
    assert task is not None
    assert task["status"] == "idle"
    assert [event["event_type"] for event in task["events"] if event["event_type"] in {
        "user_message", "assistant_message"
    }] == ["user_message", "assistant_message"]
    assert model.requests[0].prior_events[0].event_type is LoopEventType.USER_MESSAGE


def test_conversation_executor_runs_two_tool_cycles_and_returns_idle():
    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)
    model = _TwoToolCycleModel()
    tools = _LookupTools()

    result = AgentLoopExecutor(repository, model, tools).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.task.status is TaskStatus.IDLE
    assert tools.calls == 2
    event_types = [event.event_type for event in result.events]
    assert event_types.count(LoopEventType.TOOL_REQUESTED) == 2
    assert event_types.count(LoopEventType.TOOL_RESULT) == 2
    assert LoopEventType.TOOL_COMPLETED not in event_types
    assert LoopEventType.ASSISTANT_MESSAGE in event_types


def test_confirmation_required_tool_pauses_with_exact_pending_call():
    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)

    class _ApprovalModel:
        def generate(self, request, cancellation):  # type: ignore[no-untyped-def]
            return ModelResponse(
                tool_requests=(
                    ToolRequest(
                        tool_name="lookup",
                        arguments={"query": "today"},
                        call_id="call-persisted",
                    ),
                )
            )

    result = AgentLoopExecutor(repository, _ApprovalModel(), _ApprovalTools()).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert result.status is ExecutionStatus.PENDING
    assert result.task.status is TaskStatus.AWAITING_APPROVAL
    assert result.task.pending_tool_call == {
        "tool_id": 17,
        "arguments": {"query": "today"},
        "requester_agent_id": 7,
        "call_id": "call-persisted",
        "tool_name": "lookup",
    }
    approval_event = next(
        event for event in result.events if event.event_type is LoopEventType.TOOL_AWAITING_APPROVAL
    )
    assert approval_event.payload["description"] == "Look up a value."
    assert approval_event.payload["read_only"] is False


def test_runtime_approval_reuses_persisted_call_and_resumes(tmp_path):
    repository = InMemoryAgentLoopTaskRepository()
    tools = _ApprovalTools()
    runtime = AgentLoopRuntime(
        repository=repository,
        model_executor=_ConversationModel(),
        tool_executor=tools,
        workspace_root=tmp_path,
    )
    task = replace(
        _conversation_task(),
        status=TaskStatus.AWAITING_APPROVAL,
        pending_tool_call={
            "tool_id": 17,
            "arguments": {"query": "today"},
            "requester_agent_id": 7,
            "call_id": "call-persisted",
            "tool_name": "lookup",
        },
        current_turn=1,
        tool_call_count=1,
    )
    repository.save(task)

    approved = runtime.decide_approval(task.id, "approve")
    assert approved is not None
    assert runtime.wait_for_task(task.id, timeout=2.0)
    assert len(tools.approved_calls) == 1
    assert tools.approved_calls[0].call_id == "call-persisted"
    assert tools.approved_calls[0].tool_id == 17
    assert repository.get(task.id).pending_tool_call is None


def test_conversation_tool_failure_is_visible_and_reaches_next_model_turn():
    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)

    class _FailureThenReply:
        def __init__(self) -> None:
            self.requests: list[ModelRequest] = []

        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            self.requests.append(request)
            if not request.tool_results:
                return ModelResponse(tool_requests=(ToolRequest(tool_name="lookup", arguments={}),))
            return ModelResponse(final_text="The lookup failed, so I could not verify it.")

    model = _FailureThenReply()
    result = AgentLoopExecutor(repository, model, _LookupTools(fail=True)).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert result.task.status is TaskStatus.IDLE
    assert any(event.event_type is LoopEventType.TOOL_FAILED for event in result.events)
    assert model.requests[1].tool_results[0].status == "failed"


def test_submit_message_rejects_a_second_active_run(monkeypatch, tmp_path: Path):
    from apmatia.modules.agent_loops import service as service_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: type("Manager", (), {"get_agent": lambda self, _: _Agent()})())
    repository = InMemoryAgentLoopTaskRepository()
    runtime = AgentLoopRuntime(repository=repository, workspace_root=tmp_path)
    created = runtime.create_task(agent_id=7, owner_user_id=7)
    task = repository.get(created["id"])
    assert task is not None
    repository.save(replace(task, status=TaskStatus.RUNNING))

    with pytest.raises(RuntimeError, match="not idle"):
        runtime.submit_message(created["id"], "another message")


def test_malformed_tool_request_is_failed_and_given_to_next_model_turn():
    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)

    class _MalformedThenReply:
        def __init__(self) -> None:
            self.requests: list[ModelRequest] = []

        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            self.requests.append(request)
            if not request.tool_results:
                return ModelResponse(
                    tool_requests=(
                        ToolRequest(
                            tool_name="malformed_tool_call",
                            validation_error="INVALID_TOOL_CALL_JSON: {broken",
                        ),
                    )
                )
            return ModelResponse(final_text="I could not parse the tool request.")

    model = _MalformedThenReply()
    result = AgentLoopExecutor(repository, model, _LookupTools()).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert result.task.status is TaskStatus.IDLE
    assert any(
        event.event_type is LoopEventType.TOOL_FAILED
        and event.payload["error"]["code"] == "INVALID_TOOL_REQUEST"
        for event in result.events
    )
    assert model.requests[1].tool_results[0].status == "failed"


def test_malformed_memory_create_never_reaches_provider_and_returns_diagnostic_to_model():
    from apmatia.modules.agent_loops.service import parse_tool_calls

    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)
    parsed = parse_tool_calls('<tool_call>{"name":"memory_create","arguments":{"text":"' + ("x" * 100))[0]

    class _MalformedMemoryModel:
        def __init__(self) -> None:
            self.requests: list[ModelRequest] = []

        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            self.requests.append(request)
            if not request.tool_results:
                return ModelResponse(
                    tool_requests=(
                        ToolRequest(
                            tool_name=parsed.name,
                            arguments=parsed.arguments,
                            validation_error=parsed.error,
                            diagnostic=parsed.diagnostic,
                        ),
                    )
                )
            return ModelResponse(final_text="The malformed call was reported.")

    model = _MalformedMemoryModel()
    tools = _LookupTools()
    result = AgentLoopExecutor(repository, model, tools).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert tools.calls == 0
    failure = next(event for event in result.events if event.event_type is LoopEventType.TOOL_FAILED)
    assert failure.payload["tool_name"] == "memory_create"
    assert failure.payload["diagnostic"]
    assert model.requests[1].tool_results[0].status == "failed"
    assert model.requests[1].tool_results[0].error["message"] == parsed.error


def test_long_valid_tool_call_payload_reaches_normal_tool_execution():
    from apmatia.modules.agent_loops.service import parse_tool_calls

    long_text = "payload-" + ("x" * 3000)
    parsed = parse_tool_calls(
        f"<tool_call>{json.dumps({'name': 'lookup', 'arguments': {'text': long_text}})}</tool_call>"
    )[0]
    assert parsed.name == "lookup"
    assert parsed.arguments["text"] == long_text

    repository = InMemoryAgentLoopTaskRepository()
    task = _conversation_task()
    repository.save(task)

    class _LongPayloadModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            if not request.tool_results:
                return ModelResponse(
                    tool_requests=(
                        ToolRequest(
                            tool_name=parsed.name,
                            arguments=parsed.arguments,
                        ),
                    )
                )
            return ModelResponse(final_text="Long payload handled.")

    tools = _LookupTools()
    result = AgentLoopExecutor(repository, _LongPayloadModel(), tools).execute(
        AgentLoopExecutionRequest(task_id=task.id), CancellationToken()
    )

    assert result.task.status is TaskStatus.IDLE
    assert tools.calls == 1


def test_runtime_recovers_orphaned_sqlite_task_after_restart(tmp_path: Path):
    db_path = tmp_path / "loop_tasks.db"
    first = SQLiteLoopTaskBundle(db_path=db_path)
    orphan = replace(_conversation_task(), status=TaskStatus.RUNNING, execution_status=ExecutionStatus.RUNNING)
    first.tasks.save(orphan)

    restarted = AgentLoopRuntime(
        repository=SQLiteLoopTaskBundle(db_path=db_path).tasks,
        model_executor=_ConversationModel(),
        tool_executor=_LookupTools(),
        workspace_root=tmp_path,
    )

    recovered = restarted.get_task(orphan.id)
    assert recovered is not None
    assert recovered["status"] == "stopped"
    assert recovered["stop_requested"] is False
    assert any(event["event_type"] == "task_stopped" for event in recovered["events"])


def test_parse_tool_call_reports_invalid_json_and_non_object_arguments():
    from apmatia.modules.agent_loops.service import parse_tool_calls

    invalid_json = parse_tool_calls('<tool_call>{"name":"lookup","arguments":</tool_call>')
    invalid_arguments = parse_tool_calls(
        '<tool_call>{"name":"lookup","arguments":[1,2]}</tool_call>'
    )
    unterminated = parse_tool_calls('<tool_call>{"name":"lookup","arguments":{}}')

    assert invalid_json[0].error is not None
    assert "INVALID_TOOL_CALL_JSON" in invalid_json[0].error
    assert invalid_arguments[0].error == "INVALID_TOOL_ARGUMENTS: arguments must be a JSON object."
    assert unterminated[0].name == "lookup"
    assert unterminated[0].error == "MALFORMED_TOOL_CALL: unterminated tool call block."


def test_unterminated_tool_call_recovers_name_and_valid_arguments():
    from apmatia.modules.agent_loops.service import parse_tool_calls, strip_tool_calls

    calls = parse_tool_calls('<tool_call>{"name":"memory_create","arguments":{"text":"remember this"}}')

    assert calls[0].name == "memory_create"
    assert calls[0].arguments == {"text": "remember this"}
    assert calls[0].error == "MALFORMED_TOOL_CALL: unterminated tool call block."
    assert calls[0].diagnostic is None
    assert "<tool_call>" not in strip_tool_calls('<tool_call>{"name":"memory_create","arguments":{}}')


def test_truncated_unterminated_tool_call_recovers_name_and_bounded_diagnostic():
    from apmatia.modules.agent_loops.service import parse_tool_calls

    calls = parse_tool_calls('<tool_call>{"name":"memory_create","arguments":{"text":"' + ("x" * 3000))

    assert calls[0].name == "memory_create"
    assert calls[0].arguments == {}
    assert calls[0].diagnostic is not None
    assert len(calls[0].diagnostic) <= 1024


def test_unterminated_tool_call_without_name_uses_malformed_name():
    from apmatia.modules.agent_loops.service import parse_tool_calls

    calls = parse_tool_calls('<tool_call>{"arguments":{"text":"partial"}')

    assert calls[0].name == "malformed_tool_call"


def test_immediate_second_submit_does_not_leave_a_user_event(monkeypatch, tmp_path: Path):
    from apmatia.modules.agent_loops import service as service_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: type("Manager", (), {"get_agent": lambda self, _: _Agent()})())

    class _BlockingModel:
        def __init__(self) -> None:
            self.started = Event()
            self.release = Event()

        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            self.started.set()
            self.release.wait(2.0)
            return ModelResponse(final_text="Done")

    model = _BlockingModel()
    repository = InMemoryAgentLoopTaskRepository()
    runtime = AgentLoopRuntime(
        repository=repository,
        model_executor=model,
        tool_executor=_LookupTools(),
        workspace_root=tmp_path,
    )
    created = runtime.create_task(agent_id=7, owner_user_id=7)
    runtime.submit_message(created["id"], "first")
    assert model.started.wait(1.0)

    with pytest.raises(RuntimeError, match="not idle|active run"):
        runtime.submit_message(created["id"], "second")

    model.release.set()
    assert runtime.wait_for_task(created["id"], timeout=2.0)
    task = repository.get(created["id"])
    assert task is not None
    user_messages = [event for event in task.events if event.event_type is LoopEventType.USER_MESSAGE]
    assert [event.payload["text"] for event in user_messages] == ["first"]
