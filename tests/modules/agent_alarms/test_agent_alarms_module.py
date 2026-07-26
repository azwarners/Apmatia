from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.modules.agent_alarms import AlarmStatus, AgentAlarmsService
from apmatia.modules.agent_alarms.actions import ACTION_DESCRIPTORS
from apmatia.modules.agent_alarms.commands import COMMAND_DESCRIPTORS
from apmatia.modules.agent_alarms.module import AGENT_ALARMS_MODULE, register
from apmatia.modules.agent_alarms.module_views import AgentAlarmsModuleViewProvider
from apmatia.modules.agent_alarms.views import VIEW_DESCRIPTORS
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view


class _LoopHarness:
    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.runs: dict[str, dict[str, object]] = {}

    def start_loop(self, *, agent_id: int, prompt: str, model_id: int | None = None) -> dict[str, object]:
        run_id = f"loop-{len(self.start_calls) + 1}"
        self.start_calls.append(
            {
                "agent_id": agent_id,
                "prompt": prompt,
                "model_id": model_id,
                "run_id": run_id,
            }
        )
        run = self._running_run(run_id, model_id=model_id)
        self.runs[run_id] = run
        return run

    def get_loop_run(self, run_id: str) -> dict[str, object] | None:
        return self.runs.get(run_id)

    def mark_completed(self, run_id: str, *, summary: str = "Finished") -> None:
        self.runs[run_id] = {
            "id": run_id,
            "execution_status": "completed",
            "summary": summary,
            "final_text": summary,
            "task": {
                "execution_status": "completed",
                "summary": summary,
                "final_text": summary,
            },
        }

    def mark_failed(self, run_id: str, *, error: str = "Loop failed.") -> None:
        self.runs[run_id] = {
            "id": run_id,
            "execution_status": "failed",
            "error": error,
            "last_error": error,
            "task": {
                "execution_status": "failed",
                "last_error": error,
            },
        }

    @staticmethod
    def _running_run(run_id: str, *, model_id: int | None) -> dict[str, object]:
        return {
            "id": run_id,
            "execution_status": "running",
            "task": {
                "execution_status": "running",
            },
            "raw_response": {
                "selected_model_id": model_id,
            },
        }


def _service(tmp_path: Path, harness: _LoopHarness, monkeypatch) -> AgentAlarmsService:
    from apmatia.modules.agent_alarms import service as service_module

    monkeypatch.setattr(service_module, "start_agent_loop", harness.start_loop)
    monkeypatch.setattr(service_module, "get_agent_loop_run", harness.get_loop_run)
    return AgentAlarmsService(data_dir=tmp_path)


def _create_due_alarm(service: AgentAlarmsService, *, name: str = "Daily review", agent_id: int = 7, model_id: int = 11):
    return service.create_alarm(
        name=name,
        agent_id=agent_id,
        prompt="Summarize the day and draft a short update.",
        model_id=model_id,
        scheduled_start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        enabled=True,
    )


def test_agent_alarms_module_registers_registry_metadata(monkeypatch):
    registry = Registry()
    monkeypatch.setattr("apmatia.modules.agent_alarms.module.get_agent_alarm_service", lambda: None)

    register(registry)

    assert registry.list_modules(include_development=True) == [AGENT_ALARMS_MODULE]
    assert [action.action_id for action in registry.list_actions()] == [action.action_id for action in ACTION_DESCRIPTORS]
    assert [command.command_id for command in registry.list_commands()] == [command.command_id for command in COMMAND_DESCRIPTORS]
    assert [view.view_id for view in registry.list_views()] == [view.view_id for view in VIEW_DESCRIPTORS]


def test_agent_alarms_view_descriptor_exposes_create_and_row_actions():
    spec = adapt_module_view(VIEW_DESCRIPTORS[0], items=[])

    assert spec.create_form is not None
    assert [field.key for field in spec.create_form.fields] == [
        "name",
        "agent_id",
        "prompt",
        "model_id",
        "scheduled_start_date",
        "scheduled_start_time",
        "enabled",
    ]
    assert [action.intent for action in spec.view_actions] == ["create"]
    assert spec.view_actions[0].payload["command_id"] == "agent_alarms.create"
    assert [action.intent for action in spec.item_actions] == ["edit", "delete"]
    assert [action.payload["command_id"] for action in spec.item_actions] == [
        "agent_alarms.edit",
        "agent_alarms.delete",
    ]


def test_agent_alarms_module_view_provider_normalizes_alarm_payload(monkeypatch, tmp_path):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    provider = AgentAlarmsModuleViewProvider(service=service)

    alarm = provider.execute_command(
        command=type(
            "Command",
            (),
            {
                "metadata": {"verb": "create"},
            },
        )(),
        payload={
            "name": "Morning check-in",
            "agent_id": {"label": "Planner", "value": 7},
            "prompt": "Review the morning inbox.",
            "model_id": {"label": "Planner alias", "value": 11},
            "scheduled_start_date": "2026-07-13",
            "scheduled_start_time": "08:30",
            "enabled": True,
        },
        context=ModuleViewContext(),
    )

    assert alarm is not None
    assert alarm["status"] == "created"
    assert alarm["item"]["agent_id"] == 7
    assert alarm["item"]["model_id"] == 11
    assert alarm["item"]["scheduled_start_time"].startswith("2026-07-13T08:30")


def test_due_alarm_calls_agent_loops_service_and_retains_run_id(tmp_path, monkeypatch):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    alarm = _create_due_alarm(service)

    service.poll_once()

    assert harness.start_calls == [
        {
            "agent_id": 7,
            "prompt": "Summarize the day and draft a short update.",
            "model_id": 11,
            "run_id": "loop-1",
        }
    ]
    refreshed = service.get_alarm(alarm.id or 0)
    assert refreshed is not None
    assert refreshed.status == AlarmStatus.RUNNING
    assert refreshed.launched_loop_run_id == "loop-1"


def test_same_alarm_does_not_launch_two_loop_runs(tmp_path, monkeypatch):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    alarm = _create_due_alarm(service)

    service.poll_once()
    service.poll_once()

    assert len(harness.start_calls) == 1
    refreshed = service.get_alarm(alarm.id or 0)
    assert refreshed is not None
    assert refreshed.status == AlarmStatus.RUNNING
    assert refreshed.launched_loop_run_id == "loop-1"


def test_alarm_fired_loop_is_tagged_for_the_agent_contact(tmp_path, monkeypatch):
    from apmatia.modules.agent_loops import service as service_module
    from apmatia.modules.agent_loops.repository import InMemoryAgentLoopTaskRepository

    runtime = service_module.AgentLoopRuntime(repository=InMemoryAgentLoopTaskRepository(), workspace_root=tmp_path)
    runtime._executor.execute = lambda *args, **kwargs: None  # type: ignore[assignment]

    fake_agent = SimpleNamespace(
        id=7,
        name="Planner",
        owner_user_id=9,
        owner_group_id=None,
        mode=0,
        workspace_root="",
    )
    monkeypatch.setattr(
        service_module,
        "get_agent_manager",
        lambda: SimpleNamespace(get_agent=lambda _agent_id: fake_agent),
    )

    result = runtime.start_loop(agent_id=7, prompt="Review the morning inbox.", model_id=11)
    task = result["task"]

    assert task["contact_kind"] == "agent"
    assert task["contact_id"] == "7"
    assert task["metadata"]["source"] == "agent_alarms"


def test_multiple_due_alarms_can_launch_separate_loop_runs(tmp_path, monkeypatch):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    first = _create_due_alarm(service, name="Daily review", agent_id=7, model_id=11)
    second = _create_due_alarm(service, name="Late check-in", agent_id=8, model_id=12)

    service.poll_once()

    assert len(harness.start_calls) == 2
    assert {call["run_id"] for call in harness.start_calls} == {"loop-1", "loop-2"}
    refreshed_first = service.get_alarm(first.id or 0)
    refreshed_second = service.get_alarm(second.id or 0)
    assert refreshed_first is not None and refreshed_first.launched_loop_run_id is not None
    assert refreshed_second is not None and refreshed_second.launched_loop_run_id is not None
    assert refreshed_first.launched_loop_run_id != refreshed_second.launched_loop_run_id


def test_loop_completion_updates_and_disables_alarm(tmp_path, monkeypatch):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    alarm = _create_due_alarm(service)

    service.poll_once()
    run_id = harness.start_calls[0]["run_id"]
    harness.mark_completed(str(run_id), summary="Completed successfully.")
    service.poll_once()

    refreshed = service.get_alarm(alarm.id or 0)
    assert refreshed is not None
    assert refreshed.status == AlarmStatus.COMPLETED
    assert refreshed.enabled is False
    assert refreshed.launched_loop_run_id == "loop-1"
    assert refreshed.last_result == "Completed successfully."
    assert refreshed.last_error is None
    assert refreshed.completed_at is not None


def test_loop_failure_updates_and_disables_alarm(tmp_path, monkeypatch):
    harness = _LoopHarness()
    service = _service(tmp_path, harness, monkeypatch)
    alarm = _create_due_alarm(service)

    service.poll_once()
    run_id = harness.start_calls[0]["run_id"]
    harness.mark_failed(str(run_id), error="Boom")
    service.poll_once()

    refreshed = service.get_alarm(alarm.id or 0)
    assert refreshed is not None
    assert refreshed.status == AlarmStatus.FAILED
    assert refreshed.enabled is False
    assert refreshed.launched_loop_run_id == "loop-1"
    assert refreshed.last_error == "Boom"
    assert refreshed.completed_at is not None


def test_agent_alarms_package_uses_only_the_public_agent_loop_boundary():
    module_root = Path("/home/nick/ServerData/repos/apmatia/src/apmatia/modules/agent_alarms")
    forbidden_import_prefix = "apmatia.modules.agent_loops."
    forbidden_tokens = {
        "AgentLoopExecutor",
        "LoopTaskRequest",
        "ToolManagerToolExecutor",
        "prompt_llm",
        "resolve_agent_loop_workspace_root",
        "resolve_contact_roots",
    }

    source_parts: list[str] = []
    for path in module_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        source_parts.append(source)
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_import_prefix), f"{path} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(forbidden_import_prefix), f"{path} imports {module}"

    joined_source = "\n".join(source_parts)
    for token in forbidden_tokens:
        assert token not in joined_source, f"{token} should not appear in agent_alarms"
