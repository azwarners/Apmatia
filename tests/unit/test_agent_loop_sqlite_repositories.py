from __future__ import annotations

from dataclasses import replace

from apmatia.modules.agent_loops.models import AgentLoopTask, LoopEvent, LoopEventType, TaskStatus
from apmatia.modules.agent_loops.sqlite_repositories import SQLiteLoopTaskBundle


def _task(task_id: str, *, agent_id: int, status: TaskStatus = TaskStatus.IDLE) -> AgentLoopTask:
    return AgentLoopTask(
        id=task_id,
        owner_user_id=7,
        agent_id=agent_id,
        title=task_id,
        status=status,
    )


def test_sqlite_bundle_persists_ordered_transcript_across_recreation(tmp_path):
    db_path = tmp_path / "loop_tasks.db"
    first_bundle = SQLiteLoopTaskBundle(db_path=db_path)
    first_bundle.tasks.create(_task("loop_1", agent_id=11))

    first = first_bundle.tasks.append_ordered_event(
        "loop_1",
        LoopEvent(LoopEventType.USER_MESSAGE, "wrong-id", {"text": "Hello"}),
    )
    second = first_bundle.tasks.append_ordered_event(
        "loop_1",
        LoopEvent(LoopEventType.ASSISTANT_MESSAGE, "wrong-id", {"text": "Hi"}),
    )

    second_bundle = SQLiteLoopTaskBundle(db_path=db_path)
    restored = second_bundle.tasks.get("loop_1")

    assert restored is not None
    assert [event.sequence for event in restored.events] == [1, 2]
    assert [event.event_type for event in restored.events] == [
        LoopEventType.USER_MESSAGE,
        LoopEventType.ASSISTANT_MESSAGE,
    ]
    assert first.task_id == second.task_id == "loop_1"
    assert restored.next_event_sequence == 3


def test_sqlite_repository_reconciles_sequence_before_next_append(tmp_path):
    db_path = tmp_path / "loop_tasks.db"
    bundle = SQLiteLoopTaskBundle(db_path=db_path)
    bundle.tasks.create(_task("loop_reconcile", agent_id=11))
    bundle.tasks.append_event("loop_reconcile", LoopEvent(LoopEventType.USER_MESSAGE, "loop_reconcile"))

    # Simulate a task snapshot whose counter was not advanced with its event.
    task = bundle.tasks.get("loop_reconcile")
    assert task is not None
    bundle.tasks.update(replace(task, next_event_sequence=1))

    assert bundle.tasks.reconcile_next_event_sequence("loop_reconcile") == 2
    appended = bundle.tasks.append_ordered_event(
        "loop_reconcile",
        LoopEvent(LoopEventType.ASSISTANT_MESSAGE, "loop_reconcile"),
    )

    assert appended.sequence == 2
    assert bundle.tasks.get("loop_reconcile").next_event_sequence == 3


def test_sqlite_task_listing_filters_archived_and_agent_id(tmp_path):
    repository = SQLiteLoopTaskBundle(db_path=tmp_path / "loop_tasks.db").tasks
    repository.create(_task("agent_1", agent_id=1))
    repository.create(_task("agent_2", agent_id=2))
    repository.create(_task("archived", agent_id=1, status=TaskStatus.ARCHIVED))

    assert {task.id for task in repository.list_tasks()} == {"agent_1", "agent_2"}
    assert [task.id for task in repository.list_tasks(agent_id=1)] == ["agent_1"]
    assert {task.id for task in repository.list_tasks(include_archived=True)} == {
        "agent_1",
        "agent_2",
        "archived",
    }
