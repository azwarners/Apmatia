from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.modules.apmatia_agent_loops.commands import COMMAND_DESCRIPTORS
from apmatia.modules.apmatia_agent_loops.executor import AgentLoopExecutor
from apmatia.modules.apmatia_agent_loops.models import (
    AgentLoopExecutionRequest,
    AgentLoopTask,
    CancellationToken,
    ExecutionStatus,
    LoopEventType,
    ModelRequest,
    ModelResponse,
    TaskStatus,
    ToolRequest,
    ToolResult,
    new_task_id,
)
from apmatia.modules.apmatia_agent_loops.module import APMATIA_AGENT_LOOPS_MODULE, register
from apmatia.modules.apmatia_agent_loops.module_views import ApmatiaAgentLoopsModuleViewProvider
from apmatia.modules.apmatia_agent_loops.repository import InMemoryAgentLoopTaskRepository
from apmatia.modules.apmatia_agent_loops.runner import AgentLoopRuntime, LoopTaskRequest
from apmatia.modules.apmatia_agent_loops.service import EventCancellationToken, YsparrModelExecutor
from apmatia.modules.apmatia_agent_loops.state import resolve_contact_roots
from apmatia.modules.apmatia_agent_loops.views import VIEW_DESCRIPTORS
from apmatia.lib.tool_management.models import ToolDefinition as RuntimeToolDefinition


class _Token(CancellationToken):
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled

    def cancel(self) -> None:
        self.cancelled = True


class _SingleTurnModel:
    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        return ModelResponse(final_text=f"Done: {request.task.prompt}", raw_response={"turn": request.turn_index})


class _ToolRoundTripModel:
    def __init__(self) -> None:
        self.calls = 0
        self.last_request: ModelRequest | None = None

    def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
        self.calls += 1
        self.last_request = request
        if self.calls == 1:
            return ModelResponse(
                tool_requests=(ToolRequest(tool_name="lookup", arguments={"query": "alpha"}),),
                raw_response={"phase": "tool"},
            )
        return ModelResponse(final_text="All done", raw_response={"phase": "final"})


class _ToolRoundTripExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolRequest] = []

    def list_tools(self, context):
        from apmatia.modules.apmatia_agent_loops.models import ToolDefinition

        return (ToolDefinition(name="lookup"),)

    def execute(self, request: ToolRequest, context, cancellation: CancellationToken) -> ToolResult:
        self.requests.append(request)
        return ToolResult(tool_name=request.tool_name, call_id=request.call_id, status="success", output={"value": 42})


def _task_for_executor(tmp_path: Path) -> AgentLoopTask:
    roots = resolve_contact_roots("agent", 1)
    return AgentLoopTask(
        id=new_task_id(),
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Build slice",
        prompt="Complete the work",
        status=TaskStatus.QUEUED,
        execution_status=ExecutionStatus.PENDING,
        max_model_turns=3,
        max_tool_calls=3,
        workspace_root=str(roots.workspace_root),
        knowledge_root=str(roots.knowledge_root),
    )


def test_module_registers_registry_metadata_and_views():
    registry = Registry()

    register(registry)

    assert registry.list_modules() == [APMATIA_AGENT_LOOPS_MODULE]
    assert [command.command_id for command in registry.list_commands()] == [
        command.command_id for command in COMMAND_DESCRIPTORS
    ]
    assert [view.view_id for view in registry.list_views()] == sorted(view.view_id for view in VIEW_DESCRIPTORS)


def test_agent_loop_executor_completes_a_single_turn(tmp_path: Path):
    repository = InMemoryAgentLoopTaskRepository()
    task = _task_for_executor(tmp_path)
    repository.save(task)
    executor = AgentLoopExecutor(repository, _SingleTurnModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.COMPLETED
    assert result.final_text == "Done: Complete the work"
    assert result.task.status == TaskStatus.COMPLETED
    assert [event.event_type for event in result.events][:4] == [
        LoopEventType.TASK_STARTED,
        LoopEventType.MODEL_TURN_STARTED,
        LoopEventType.MODEL_TURN_COMPLETED,
        LoopEventType.TASK_COMPLETED,
    ]


def test_agent_loop_executor_executes_tools_and_feeds_results_back(tmp_path: Path):
    repository = InMemoryAgentLoopTaskRepository()
    task = _task_for_executor(tmp_path)
    repository.save(task)
    model = _ToolRoundTripModel()
    tool_executor = _ToolRoundTripExecutor()
    executor = AgentLoopExecutor(repository, model, tool_executor)

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.COMPLETED
    assert result.final_text == "All done"
    assert tool_executor.requests[0].tool_name == "lookup"
    assert model.last_request is not None
    assert model.last_request.tool_results[0].status == "success"
    assert any(event.event_type == LoopEventType.TOOL_REQUESTED for event in result.events)
    assert any(event.event_type == LoopEventType.TOOL_COMPLETED for event in result.events)


def test_agent_loop_executor_records_model_activity_updates(tmp_path: Path):
    class _ActivityModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            assert callable(request.activity_sink)
            request.activity_sink(
                {
                    "provider": "test-backend",
                    "endpoint": "/v1/chat/completions",
                    "text": "streaming chunk",
                    "stats": {"tokens": 1},
                }
            )
            return ModelResponse(final_text="All done")

    repository = InMemoryAgentLoopTaskRepository()
    task = _task_for_executor(tmp_path)
    repository.save(task)
    executor = AgentLoopExecutor(repository, _ActivityModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.COMPLETED
    assert result.task.status == TaskStatus.COMPLETED
    assert result.task.metadata["live_activity"]["text"] == "streaming chunk"
    assert any(event.event_type == LoopEventType.MODEL_ACTIVITY for event in result.events)


def test_agent_loop_executor_continues_until_loop_status_done(tmp_path: Path):
    class _LoopingModel:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            self.calls += 1
            if self.calls == 1:
                return ModelResponse(
                    final_text=(
                        "I am Karen Smith, Agent (ID 7).\n"
                        "<loop_status>{"
                        '"done": false, '
                        '"summary": "Introduced myself.", '
                        '"completed_items": [], '
                        '"remaining_items": ["State your name and title."], '
                        '"next_action": "Introduce myself and continue.", '
                        '"executive_analysis": "I should keep going."'
                        "}</loop_status>"
                    )
                )
            return ModelResponse(
                final_text=(
                    "I have now completed the checklist.\n"
                    "<loop_status>{"
                    '"done": true, '
                    '"summary": "Checklist complete.", '
                    '"completed_items": ["State your name and title."], '
                    '"remaining_items": [], '
                    '"next_action": "", '
                    '"executive_analysis": "Ready to close out."'
                    "}</loop_status>"
                )
            )

    repository = InMemoryAgentLoopTaskRepository()
    task = replace(_task_for_executor(tmp_path), max_model_turns=3)
    repository.save(task)
    executor = AgentLoopExecutor(repository, _LoopingModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.COMPLETED
    assert result.model_turns == 2
    assert result.task.metadata["loop_status"]["done"] is True
    assert result.task.metadata["summary"] == "Checklist complete."
    assert any(
        event.event_type == LoopEventType.MODEL_TURN_STARTED and event.payload.get("turn_index") == 2
        for event in result.events
    )


def test_agent_loop_executor_honors_stop_request_saved_during_model_turn(tmp_path: Path):
    repository = InMemoryAgentLoopTaskRepository()
    task = _task_for_executor(tmp_path)
    repository.save(task)

    class _StopRequestModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            repository.save(
                replace(
                    request.task,
                    status=TaskStatus.STOPPING,
                    stop_requested=True,
                )
            )
            return ModelResponse(final_text="should not complete")

    executor = AgentLoopExecutor(repository, _StopRequestModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.CANCELLED
    assert result.task.status == TaskStatus.CANCELLED
    assert result.stop_reason == "cancelled"


def test_agent_loop_executor_honors_cancellation_after_model_call(tmp_path: Path):
    class _CancellingModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            cancellation.cancel()
            return ModelResponse(final_text="should not finish")

    repository = InMemoryAgentLoopTaskRepository()
    task = _task_for_executor(tmp_path)
    repository.save(task)
    executor = AgentLoopExecutor(repository, _CancellingModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.CANCELLED
    assert result.task.status == TaskStatus.CANCELLED
    assert any(event.event_type == LoopEventType.CANCELLATION_REQUESTED for event in result.events)


def test_agent_loop_executor_stops_when_model_turn_limit_is_reached(tmp_path: Path):
    class _ToolingModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            return ModelResponse(tool_requests=(ToolRequest(tool_name="lookup", arguments={}),))

    repository = InMemoryAgentLoopTaskRepository()
    task = replace(_task_for_executor(tmp_path), max_model_turns=1)
    repository.save(task)
    executor = AgentLoopExecutor(repository, _ToolingModel(), _ToolRoundTripExecutor())

    result = executor.execute(AgentLoopExecutionRequest(task_id=str(task.id or "")), _Token())

    assert result.status == ExecutionStatus.LIMIT_REACHED
    assert result.task.status == TaskStatus.LIMIT_REACHED
    assert result.stop_reason == "max_model_turns"


def test_agent_loop_runtime_persists_tasks_and_transcripts(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))

    class _RuntimeModel:
        def generate(self, request: ModelRequest, cancellation: CancellationToken) -> ModelResponse:
            if request.tool_results:
                return ModelResponse(final_text="finished")
            return ModelResponse(
                tool_requests=(ToolRequest(tool_name="lookup", arguments={"query": "alpha"}),),
            )

    class _RuntimeTools:
        def list_tools(self, context):
            from apmatia.modules.apmatia_agent_loops.models import ToolDefinition

            return (ToolDefinition(name="lookup"),)

        def execute(self, request: ToolRequest, context, cancellation: CancellationToken) -> ToolResult:
            return ToolResult(tool_name=request.tool_name, call_id=request.call_id, status="success", output="ok")

    runtime = AgentLoopRuntime(repository=InMemoryAgentLoopTaskRepository(), model_executor=_RuntimeModel(), tool_executor=_RuntimeTools())
    started = runtime.start_task(
        LoopTaskRequest(
            owner_user_id=7,
            contact_kind="agent",
            contact_id=1,
            title="Runtime task",
            prompt="Do the work",
            checklist=[{"label": "Inspect"}],
            participant_agent_ids=[1],
            agent_id=1,
            allow_tools=True,
            max_iterations=3,
        )
    )

    assert started["status"] in {"queued", "running", "completed"}
    assert runtime.wait_for_task(str(started["id"]), timeout=2.0) is True

    task = runtime.get_task(str(started["id"]))
    assert task is not None
    assert task["status"] == "completed"
    transcript = runtime.get_task_transcript(str(started["id"]))
    assert transcript is not None
    assert "finished" in transcript["content"]


def test_agent_loop_runtime_stop_task_cancels_when_no_worker_thread_exists(tmp_path: Path):
    repository = InMemoryAgentLoopTaskRepository()
    runtime = AgentLoopRuntime(repository=repository)
    task = _task_for_executor(tmp_path)
    task = replace(task, status=TaskStatus.RUNNING, execution_status=ExecutionStatus.RUNNING)
    repository.save(task)

    stopped = runtime.stop_task(str(task.id or ""))

    assert stopped is not None
    assert stopped["status"] == "cancelled"
    assert stopped["execution_status"] == "cancelled"
    assert stopped["stop_requested"] is True


def test_tool_manager_tool_executor_lists_and_executes_agent_tools(monkeypatch, tmp_path: Path):
    class _Agent:
        active_model_id = None
        default_model_id = None
        tool_ids = [17]

    class _ToolManager:
        def __init__(self) -> None:
            self.calls: list[object] = []

        def list_tools_available_to_agent(self, agent_id: int):
            return [
                RuntimeToolDefinition(
                    id=17,
                    name="lookup",
                    description="Search the workspace.",
                    input_schema={"type": "object"},
                    provider_id="builtin.lookup",
                    enabled=True,
                    confirmation_required=False,
                    read_only=True,
                    metadata={"scope": "workspace"},
                )
            ]

        def execute_tool_call(self, tool_call):
            self.calls.append(tool_call)
            return type(
                "Result",
                (),
                {
                    "status": "success",
                    "result": {"value": 42},
                    "error": None,
                    "metadata": {"tool_id": tool_call.tool_id},
                },
            )()

    tool_manager = _ToolManager()

    from apmatia.modules.apmatia_agent_loops import service as service_module
    import apmatia.core.tool_management_runtime as tool_runtime_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: type("AgentManager", (), {"get_agent": lambda self, agent_id: _Agent()})())
    monkeypatch.setattr(tool_runtime_module, "get_tool_manager", lambda: tool_manager)

    task = AgentLoopTask(
        id="loop_test",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Investigation",
        prompt="Do the work",
        agent_id=7,
    )
    context = type("Context", (), {"task": task})()
    executor = service_module.ToolManagerToolExecutor()

    available_tools = executor.list_tools(context)
    assert [tool.name for tool in available_tools] == ["lookup"]
    assert available_tools[0].metadata["tool_id"] == 17

    result = executor.execute(
        type("Request", (), {"tool_name": "lookup", "arguments": {"query": "alpha"}, "call_id": "call_1"})(),
        context,
        EventCancellationToken(),
    )

    assert result.status == "success"
    assert result.output == {"value": 42}
    assert tool_manager.calls[0].requester_agent_id == 7
    assert tool_manager.calls[0].tool_id == 17


def test_module_view_provider_lists_contacts_and_stop_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    provider = ApmatiaAgentLoopsModuleViewProvider()
    context = ModuleViewContext(user_id=7, group_ids=frozenset({9}))

    contacts_view = next(view for view in VIEW_DESCRIPTORS if view.metadata.get("object_type") == "contact")
    class _AgentManager:
        def list_agents(self):
            return [type("Agent", (), {"id": 1, "name": "Ada", "updated_at": None, "tool_ids": []})()]

    class _GroupManager:
        def list_groups(self):
            return [type("Group", (), {"id": 9, "name": "Ops", "updated_at": None})()]

    runtime = AgentLoopRuntime(repository=InMemoryAgentLoopTaskRepository())
    saved_task = _task_for_executor(tmp_path)
    runtime._repository.save(saved_task)  # type: ignore[attr-defined]

    from apmatia.modules.apmatia_agent_loops import module_views as module_views_module

    monkeypatch.setattr(module_views_module, "get_agent_manager", lambda: _AgentManager())
    monkeypatch.setattr(module_views_module, "get_group_manager", lambda: _GroupManager())
    monkeypatch.setattr(module_views_module, "get_agent_loop_runner", lambda: runtime)

    items = provider.list_items(view=contacts_view, context=context)
    assert {item["contact_kind"] for item in items} == {"agent", "group"}
    stop_result = provider.execute_command(
        command=COMMAND_DESCRIPTORS[0],
        payload={"task_id": str(saved_task.id)},
        context=context,
    )
    assert stop_result is not None
    assert stop_result["status"] == "cancelled"


def test_file_agent_loop_task_repository_ignores_empty_task_files(tmp_path: Path):
    from apmatia.modules.apmatia_agent_loops.repository import FileAgentLoopTaskRepository

    repository = FileAgentLoopTaskRepository(tmp_path)
    task_path = tmp_path / "tasks" / "loop_empty.json"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text("", encoding="utf-8")

    assert repository.get("loop_empty") is None
    assert repository.list_all() == []


def test_ysparr_model_executor_uses_agent_model_config_and_tool_calls(monkeypatch):
    class _Agent:
        active_model_id = 11
        default_model_id = None
        prompt_id = 21
        name = "Karen Smith"

    class _LLMConfig:
        id = 11
        backend = "openai_compatible"
        provider_name = "test-provider"
        model_url = "http://localhost:1234"

    class _AgentManager:
        def get_agent(self, agent_id: int):
            return _Agent()

        def get_agent_system_prompt(self, agent_id: int):
            return (
                "You are Karen Smith.\n\n"
                "Purpose: Support the user with reliable and focused help.\n\n"
                "Tool policy: Use tools only when they clearly help accomplish the task."
            )

    class _LLMConfigManager:
        def get_config(self, config_id: int):
            return _LLMConfig() if config_id == 11 else None

        def list_configs(self):
            return [_LLMConfig()]

    captured = {}

    def _prompt_llm(*, prompt, context=None, llm_config=None, request_metadata=None, **kwargs):
        captured["prompt"] = prompt
        captured["context"] = context
        captured["llm_config"] = llm_config
        captured["request_metadata"] = request_metadata
        captured["stop_event"] = kwargs.get("stop_event")
        captured["on_event"] = kwargs.get("on_event")
        if callable(captured["on_event"]):
            captured["on_event"](
                {
                    "provider": "test",
                    "endpoint": "/v1/chat/completions",
                    "text": "chunk",
                    "stats": {"tokens": 1},
                }
            )
        return 'Working <tool_call>{"name": "lookup", "arguments": {"query": "alpha"}}</tool_call>'

    from apmatia.modules.apmatia_agent_loops import service as service_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: _AgentManager())
    monkeypatch.setattr(service_module, "get_llm_config_manager", lambda: _LLMConfigManager())
    monkeypatch.setattr(service_module, "prompt_llm", _prompt_llm)

    task = AgentLoopTask(
        id="loop_test",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Investigation",
        prompt="Do the work",
        agent_id=7,
    )
    from apmatia.modules.apmatia_agent_loops.models import ToolDefinition

    request = ModelRequest(
        task_id="loop_test",
        task=task,
        turn_index=1,
        available_tools=(ToolDefinition(name="lookup", description="Search the workspace."),),
    )

    response = YsparrModelExecutor().generate(request, EventCancellationToken())

    assert captured["llm_config"].id == 11
    assert "Investigation" in captured["context"]
    assert "You are Karen Smith." in captured["context"]
    assert "lookup" in captured["context"]
    assert "Search the workspace." in captured["context"]
    assert captured["stop_event"] is not None
    assert callable(captured["on_event"])
    assert isinstance(captured["request_metadata"].get("chat_messages"), list)
    assert [message["role"] for message in captured["request_metadata"]["chat_messages"]] == ["system", "user"]
    assert response.final_text == "Working"
    assert [tool.tool_name for tool in response.tool_requests] == ["lookup"]


def test_ysparr_model_executor_streams_visible_chunks_into_activity_sink(monkeypatch):
    class _Agent:
        active_model_id = 11
        default_model_id = None

    class _LLMConfig:
        id = 11
        backend = "openai_compatible"
        provider_name = "test-provider"
        model_url = "http://localhost:1234"

    class _AgentManager:
        def get_agent(self, agent_id: int):
            return _Agent()

    class _LLMConfigManager:
        def get_config(self, config_id: int):
            return _LLMConfig() if config_id == 11 else None

        def list_configs(self):
            return [_LLMConfig()]

    captured: dict[str, list[dict[str, object]]] = {"activity": []}

    def _prompt_llm(*, prompt, context=None, llm_config=None, request_metadata=None, **kwargs):
        assert callable(kwargs.get("on_chunk"))
        assert callable(kwargs.get("on_event"))
        kwargs["on_chunk"]("Hel")
        kwargs["on_chunk"]("lo ")
        kwargs["on_chunk"]("<tool_call>{\"name\": \"lookup\"}</tool_call>")
        kwargs["on_chunk"]("world")
        kwargs["on_event"](
            {
                "provider": "test",
                "endpoint": "/v1/chat/completions",
                "text": "ignored",
                "stats": {"tokens": 1},
            }
        )
        return 'Hello <tool_call>{"name": "lookup", "arguments": {"query": "alpha"}}</tool_call> world'

    from apmatia.modules.apmatia_agent_loops import service as service_module

    monkeypatch.setattr(service_module, "get_agent_manager", lambda: _AgentManager())
    monkeypatch.setattr(service_module, "get_llm_config_manager", lambda: _LLMConfigManager())
    monkeypatch.setattr(service_module, "prompt_llm", _prompt_llm)

    task = AgentLoopTask(
        id="loop_test",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Investigation",
        prompt="Do the work",
        agent_id=7,
    )

    def _activity_sink(payload: dict[str, object]) -> None:
        captured["activity"].append(dict(payload))

    request = ModelRequest(task_id="loop_test", task=task, turn_index=1, activity_sink=_activity_sink)

    response = YsparrModelExecutor().generate(request, EventCancellationToken())

    assert response.final_text == "Hello  world"
    assert captured["activity"]
    assert captured["activity"][-1]["text"] == "Hello world"
    assert captured["activity"][-1]["provider"] == "test"
    assert captured["activity"][-1]["endpoint"] == "/v1/chat/completions"
