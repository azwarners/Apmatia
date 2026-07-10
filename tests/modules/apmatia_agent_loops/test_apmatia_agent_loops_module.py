from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import Registry
from apmatia.modules.apmatia_agent_loops.module import APMATIA_AGENT_LOOPS_MODULE, register
from apmatia.modules.apmatia_agent_loops.commands import COMMAND_DESCRIPTORS
from apmatia.modules.apmatia_agent_loops.module_views import ApmatiaAgentLoopsModuleViewProvider
from apmatia.modules.apmatia_agent_loops import prompt_helpers
from apmatia.modules.apmatia_agent_loops.records import LoopTaskRecord, save_task_record
from apmatia.modules.apmatia_agent_loops.runner import ApmatiaAgentLoopRunner, LoopTaskRequest
from apmatia.modules.apmatia_agent_loops.tools import agent_loop_tool_definitions
from apmatia.modules.apmatia_agent_loops.views import VIEW_DESCRIPTORS


def test_agent_loops_module_registers_module_metadata_and_views():
    registry = Registry()

    register(registry)

    assert registry.list_modules() == [APMATIA_AGENT_LOOPS_MODULE]
    assert [command.command_id for command in registry.list_commands()] == [
        command.command_id for command in COMMAND_DESCRIPTORS
    ]
    assert [view.view_id for view in registry.list_views()] == sorted(view.view_id for view in VIEW_DESCRIPTORS)


def test_agent_loops_module_view_provider_stops_a_run_via_module_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    provider = ApmatiaAgentLoopsModuleViewProvider()
    command = COMMAND_DESCRIPTORS[0]
    context = ModuleViewContext(user_id=7, group_ids=frozenset({9}))

    with patch("apmatia.modules.apmatia_agent_loops.module_views.get_agent_loop_runner") as mock_runner:
        mock_runner.return_value.stop_task.return_value = {"status": "stopped", "task_id": "loop-123"}
        result = provider.execute_command(command=command, payload={"task_id": "loop-123"}, context=context)

    mock_runner.return_value.stop_task.assert_called_once_with("loop-123")
    assert result == {"status": "stopped", "task_id": "loop-123"}


def test_agent_loops_module_view_provider_lists_contacts_runs_workspace_and_knowledge(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    provider = ApmatiaAgentLoopsModuleViewProvider()
    context = ModuleViewContext(user_id=7, group_ids=frozenset({9}))

    agent_manager = SimpleNamespace(
        list_agents=lambda: [
            SimpleNamespace(id=1, name="Ada", active_model_id="model-a", updated_at="2026-07-08T10:00:00"),
            SimpleNamespace(id=2, name="Bea", default_model_id="model-b", updated_at="2026-07-08T11:00:00"),
        ]
    )
    group_manager = SimpleNamespace(
        list_groups=lambda: [
            SimpleNamespace(id=9, name="Ops", description="Shared loop group", updated_at="2026-07-08T12:00:00"),
        ]
    )
    agent_workspace = tmp_path / "workspace" / "apmatia_agent_loops" / "workspace" / "agent-1"
    agent_workspace.mkdir(parents=True, exist_ok=True)
    (agent_workspace / "brief.txt").write_text("agent workspace", encoding="utf-8")
    agent_knowledge = tmp_path / "workspace" / "knowledge" / "agent-1"
    agent_knowledge.mkdir(parents=True, exist_ok=True)
    (agent_knowledge / "notes.md").write_text("agent knowledge", encoding="utf-8")
    group_workspace = tmp_path / "workspace" / "apmatia_agent_loops" / "workspace" / "group-9"
    group_workspace.mkdir(parents=True, exist_ok=True)
    (group_workspace / "plan.txt").write_text("group workspace", encoding="utf-8")

    save_task_record(
        LoopTaskRecord(
            task_id="loop-1",
            owner_user_id=7,
            contact_kind="agent",
            contact_id=1,
            title="Agent loop",
            prompt="Do the thing",
            status="running",
            discussion_id="disc-1",
            agent_id=1,
            participant_agent_ids=[1],
            chat_mode="single",
            summary="Make progress",
            workspace_root=str(agent_workspace),
            knowledge_root=str(agent_knowledge),
            updated_at="2026-07-08T12:00:00",
        )
    )
    save_task_record(
        LoopTaskRecord(
            task_id="loop-2",
            owner_user_id=7,
            contact_kind="group",
            contact_id=9,
            title="Group loop",
            prompt="Coordinate the group",
            status="completed",
            discussion_id="disc-2",
            participant_agent_ids=[1, 2],
            chat_mode="round_robin",
            summary="Finished the checklist",
            executive_analysis="Ready to hand back to the user.",
            workspace_root=str(group_workspace),
            knowledge_root=str(tmp_path / "workspace" / "knowledge" / "group-9"),
            updated_at="2026-07-08T13:00:00",
        )
    )

    with (
        patch("apmatia.modules.apmatia_agent_loops.module_views.get_agent_manager", return_value=agent_manager),
        patch("apmatia.modules.apmatia_agent_loops.module_views.get_group_manager", return_value=group_manager),
    ):
        contacts_view = VIEW_DESCRIPTORS[0]
        runs_view = VIEW_DESCRIPTORS[1]
        workspace_view = VIEW_DESCRIPTORS[2]
        knowledge_view = VIEW_DESCRIPTORS[3]

        contacts = provider.list_items(view=contacts_view, context=context)
        runs = provider.list_items(view=runs_view, context=context)
        workspace_items = provider.list_items(view=workspace_view, context=context)
        knowledge_items = provider.list_items(view=knowledge_view, context=context)

    assert [item["title"] for item in contacts] == ["Ada", "Bea", "Ops"]
    assert contacts[0]["task_count"] == 1
    assert contacts[1]["task_count"] == 0
    assert contacts[2]["task_count"] == 1

    assert [item["id"] for item in runs] == ["loop-2", "loop-1"]
    assert runs[0]["status"] == "completed"
    assert runs[0]["summary"] == "Finished the checklist"
    assert runs[0]["workspace"] == str(group_workspace)
    assert runs[1]["status"] == "running"
    assert runs[1]["task_id"] == "loop-1"
    assert runs[1]["prompt"] == "Do the thing"
    assert runs[1]["discussion_id"] == "disc-1"
    assert runs[1]["workspace_root"] == str(agent_workspace)
    assert runs[1]["knowledge_root"] == str(agent_knowledge)

    assert [item["path"] for item in workspace_items] == [
        str(agent_workspace / "brief.txt"),
        str(group_workspace / "plan.txt"),
    ]
    assert {item["kind"] for item in workspace_items} == {"workspace"}

    assert [item["path"] for item in knowledge_items] == [
        str(agent_knowledge / "notes.md"),
    ]
    assert {item["kind"] for item in knowledge_items} == {"knowledge"}


def test_agent_loops_runner_completes_a_task_and_persists_history(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    transcript = {
        "messages": [
            {
                "role": "assistant",
                "text": (
                    "Working through the checklist.\n\n"
                    '<loop_status>{"done": true, "summary": "Finished the requested work.", '
                    '"completed_items": ["Inspect", "Implement"], "remaining_items": [], '
                    '"next_action": "None", "executive_analysis": "The task is complete and ready to hand back."}</loop_status>'
                ),
            }
        ]
    }

    with (
        patch(
            "apmatia.modules.apmatia_agent_loops.runner.discussion_state.create_discussion",
            return_value={"discussion_id": "disc-1"},
        ),
        patch("apmatia.modules.apmatia_agent_loops.runner.start_prompt_for_discussion") as start_prompt,
        patch("apmatia.modules.apmatia_agent_loops.runner.wait_for_prompt_completion", return_value=True),
        patch("apmatia.modules.apmatia_agent_loops.runner.get_discussion_transcript", return_value=transcript),
    ):
        started = runner.start_task(
            LoopTaskRequest(
                owner_user_id=7,
                contact_kind="agent",
                contact_id=1,
                title="Complete work",
                prompt="Finish the checklist",
                checklist=[{"label": "Inspect"}, {"label": "Implement"}],
                agent_id=1,
                allow_tools=True,
                max_iterations=3,
            )
        )
        assert started["status"] == "running"
        assert runner.wait_for_task(started["task_id"], timeout=2.0) is True

    task = runner.get_task(started["task_id"])
    assert task is not None
    assert task["status"] == "completed"
    assert task["summary"] == "Finished the requested work."
    assert task["executive_analysis"] == "The task is complete and ready to hand back."
    assert task["discussion_id"] == "disc-1"
    assert task["events"][0]["type"] == "task_started"
    assert task["events"][1]["type"] == "iteration_started"
    assert task["events"][2]["type"] == "loop_status"
    assert [item["label"] for item in task["checklist"]] == ["Inspect", "Implement"]
    start_prompt.assert_called_once()


def test_agent_loops_runner_adds_agent_verification_checklist_item(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    with (
        patch(
            "apmatia.modules.apmatia_agent_loops.runner.discussion_state.create_discussion",
            return_value={"discussion_id": "disc-2"},
        ),
        patch("apmatia.modules.apmatia_agent_loops.runner.start_prompt_for_discussion"),
        patch("apmatia.modules.apmatia_agent_loops.runner.wait_for_prompt_completion", return_value=True),
        patch(
            "apmatia.modules.apmatia_agent_loops.runner.get_discussion_transcript",
            return_value={"messages": []},
        ),
    ):
        started = runner.start_task(
            LoopTaskRequest(
                owner_user_id=7,
                contact_kind="agent",
                contact_id=1,
                title="Create agents",
                prompt="Create three agents for the team",
                checklist=[{"label": "Create the org chart"}],
                agent_id=1,
                allow_tools=True,
                max_iterations=1,
            )
        )
        assert runner.wait_for_task(started["task_id"], timeout=2.0) is True

    task = runner.get_task(started["task_id"])
    assert task is not None
    assert task["checklist"][-1]["label"] == "Verify requested agents exist with list_agents"


def test_agent_loops_runner_stops_a_task(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    record = LoopTaskRecord(
        task_id="loop-stop",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Stop me",
        prompt="Hold on",
        status="running",
        discussion_id="disc-stop",
        agent_id=1,
    )
    save_task_record(record)

    with patch(
        "apmatia.modules.apmatia_agent_loops.runner.stop_prompt_for_discussion",
        return_value=True,
    ) as stop_prompt, patch.object(runner, "_raise_system_exit_in_thread", return_value=True) as hard_stop:
        stopped = runner.stop_task("loop-stop")

    assert stopped is not None
    assert stopped["status"] == "stopped"
    assert stopped["stop_requested"] is True
    stop_prompt.assert_called_once_with("disc-stop")
    hard_stop.assert_not_called()


def test_agent_loops_runner_stops_a_task_even_if_record_write_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    record = LoopTaskRecord(
        task_id="loop-stop-readonly",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Stop me",
        prompt="Hold on",
        status="running",
        discussion_id="disc-stop-readonly",
        agent_id=1,
    )
    save_task_record(record)

    with patch(
        "apmatia.modules.apmatia_agent_loops.runner.update_task_record",
        side_effect=OSError("read-only filesystem"),
    ), patch(
        "apmatia.modules.apmatia_agent_loops.runner.stop_prompt_for_discussion",
        return_value=True,
    ), patch.object(runner, "_raise_system_exit_in_thread", return_value=True):
        stopped = runner.stop_task("loop-stop-readonly")

    assert stopped is not None
    assert stopped["status"] == "stopped"
    assert stopped["stop_requested"] is True
    listed = runner.get_task("loop-stop-readonly")
    assert listed is not None
    assert listed["status"] == "stopped"
    assert listed["stop_requested"] is True


def test_agent_loops_runner_honors_persistent_stop_requests_before_prompting(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    save_task_record(
        LoopTaskRecord(
            task_id="loop-stop-2",
            owner_user_id=7,
            contact_kind="agent",
            contact_id=1,
            title="Stop before prompt",
            prompt="Do not start",
            status="running",
            stop_requested=True,
            agent_id=1,
        )
    )

    with (
        patch("apmatia.modules.apmatia_agent_loops.runner.discussion_state.create_discussion") as create_discussion,
        patch("apmatia.modules.apmatia_agent_loops.runner.start_prompt_for_discussion") as start_prompt,
        patch("apmatia.modules.apmatia_agent_loops.runner.wait_for_prompt_completion") as wait_for_prompt,
        patch("apmatia.modules.apmatia_agent_loops.runner.get_discussion_transcript") as get_transcript,
    ):
        runner._run_task("loop-stop-2")

    task = runner.get_task("loop-stop-2")
    assert task is not None
    assert task["status"] == "stopped"
    assert task["stop_requested"] is True
    create_discussion.assert_not_called()
    start_prompt.assert_not_called()
    wait_for_prompt.assert_not_called()
    get_transcript.assert_not_called()


def test_agent_loops_runner_raises_system_exit_in_live_task_thread():
    runner = ApmatiaAgentLoopRunner()
    thread = SimpleNamespace(ident=12345, is_alive=lambda: True)

    with patch("ctypes.pythonapi.PyThreadState_SetAsyncExc", return_value=1) as inject:
        assert runner._raise_system_exit_in_thread(thread) is True

    inject.assert_called_once()


def test_agent_loops_runner_polls_for_stop_requests_while_waiting(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    runner = ApmatiaAgentLoopRunner()

    running_record = LoopTaskRecord(
        task_id="loop-wait-1",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Wait for stop",
        prompt="Keep going",
        status="running",
        agent_id=1,
    )
    stopped_record = LoopTaskRecord(
        task_id="loop-wait-1",
        owner_user_id=7,
        contact_kind="agent",
        contact_id=1,
        title="Wait for stop",
        prompt="Keep going",
        status="stopping",
        stop_requested=True,
        agent_id=1,
    )

    with (
        patch.object(runner, "_load_task", side_effect=[running_record, running_record, stopped_record]),
        patch("apmatia.modules.apmatia_agent_loops.runner.wait_for_prompt_completion", side_effect=[False, False, False]),
    ):
        result = runner._wait_for_prompt_completion_or_stop("loop-wait-1", "disc-wait", poll_seconds=0.01)

    assert result is False


def test_agent_loop_tool_definitions_expose_list_agents():
    definitions = agent_loop_tool_definitions()
    assert [definition["name"] for definition in definitions] == ["list_agents"]


def test_agent_loops_prompt_helpers_run_without_touching_current_discussion(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    import importlib

    discussions_module = importlib.reload(importlib.import_module("apmatia.lib.discussions"))
    monkeypatch.setattr(prompt_helpers, "discussion_state", discussions_module.discussion_state)
    created = discussions_module.discussion_state.create_discussion(owner_user_id=101, title="Explicit Thread")

    def fake_prompt_llm(**kwargs):
        if kwargs.get("on_chunk") is not None:
            kwargs["on_chunk"]("Assistant reply.")
        return "Assistant reply."

    monkeypatch.setattr(discussions_module, "prompt_llm", fake_prompt_llm)

    discussion_id = prompt_helpers.start_prompt_for_discussion(
        discussion_id=str(created["discussion_id"]),
        prompt="Hello explicit discussion",
    )

    assert discussion_id == str(created["discussion_id"])
    assert prompt_helpers.wait_for_prompt_completion(discussion_id, timeout=2.0) is True
    transcript = prompt_helpers.get_discussion_transcript(discussion_id)
    assert "Assistant reply." in transcript["content"]
