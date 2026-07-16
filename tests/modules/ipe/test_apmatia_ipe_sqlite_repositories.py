from __future__ import annotations

from datetime import date, datetime, timezone

from apmatia.modules.ipe.models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask
from apmatia.modules.ipe.sqlite_repositories import IpeTables, SQLiteIpeBundle


def test_sqlite_ipe_bundle_round_trips_all_object_types(tmp_path):
    bundle = SQLiteIpeBundle(tmp_path / "ipe.sqlite")

    idea = CapturedIdea(
        id="idea-1",
        owner_user_id=7,
        owner_group_id=9,
        title="Launch productivity assistant",
        body="Sketch the first workflow.",
        tags=("planning", "focus"),
    )
    task = IpeTask(
        id="task-1",
        owner_user_id=7,
        title="Review weekly priorities",
        project_id="project-1",
        due_at=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
    )
    project = IpeProject(
        id="project-1",
        owner_user_id=7,
        name="Launch productivity assistant",
        target_on=date(2026, 7, 31),
        source_idea_id="idea-1",
    )
    habit = Habit(
        id="habit-1",
        owner_user_id=7,
        name="Daily planning",
        streak_count=4,
        completion_timestamps=[
            datetime(2026, 6, 29, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 28, 8, 0, tzinfo=timezone.utc),
        ],
        source_idea_id="idea-2",
    )
    event = CalendarEvent(
        id="event-1",
        owner_user_id=7,
        title="Team sync",
        start_at=datetime(2026, 6, 30, 15, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 30, 15, 30, tzinfo=timezone.utc),
        attendee_ids=("friend-1",),
        source_idea_id="idea-3",
    )

    idea_id = bundle.ideas.create(idea)
    task_id = bundle.tasks.create(task)
    project_id = bundle.projects.create(project)
    habit_id = bundle.habits.create(habit)
    event_id = bundle.calendar_events.create(event)

    assert idea_id == 1
    assert task_id == 1
    assert project_id == 1
    assert habit_id == 1
    assert event_id == 1

    loaded_idea = bundle.ideas.get(1)
    loaded_task = bundle.tasks.get(1)
    loaded_project = bundle.projects.get(1)
    loaded_habit = bundle.habits.get(1)
    loaded_event = bundle.calendar_events.get(1)

    assert loaded_idea is not None
    assert loaded_idea.id == 1
    assert loaded_idea.owner_user_id == 7
    assert loaded_idea.owner_group_id == 9
    assert loaded_idea.tags == ("planning", "focus")

    assert loaded_task is not None
    assert loaded_task.project_id == "project-1"
    assert loaded_task.due_at == datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc)

    assert loaded_project is not None
    assert loaded_project.source_idea_id == "idea-1"
    assert loaded_project.target_on == date(2026, 7, 31)
    assert loaded_project.source_task_id is None

    assert loaded_habit is not None
    assert loaded_habit.streak_count == 4
    assert loaded_habit.source_idea_id == "idea-2"
    assert len(loaded_habit.completion_timestamps) == 2

    assert loaded_event is not None
    assert loaded_event.attendee_ids == ("friend-1",)
    assert loaded_event.source_idea_id == "idea-3"

    loaded_idea.title = "Updated idea"
    bundle.ideas.update(loaded_idea)
    assert bundle.ideas.get(1).title == "Updated idea"

    loaded_task.title = "Updated task"
    bundle.tasks.update(loaded_task)
    assert bundle.tasks.get(1).title == "Updated task"

    loaded_project.name = "Updated project"
    bundle.projects.update(loaded_project)
    assert bundle.projects.get(1).name == "Updated project"

    loaded_habit.name = "Updated habit"
    bundle.habits.update(loaded_habit)
    assert bundle.habits.get(1).name == "Updated habit"

    loaded_event.title = "Updated event"
    bundle.calendar_events.update(loaded_event)
    assert bundle.calendar_events.get(1).title == "Updated event"

    assert bundle.ideas.delete(1) is True
    assert bundle.tasks.delete(1) is True
    assert bundle.projects.delete(1) is True
    assert bundle.habits.delete(1) is True
    assert bundle.calendar_events.delete(1) is True

    assert bundle.ideas.list_all() == []
    assert bundle.tasks.list_all() == []
    assert bundle.projects.list_all() == []
    assert bundle.habits.list_all() == []
    assert bundle.calendar_events.list_all() == []
