from __future__ import annotations

from datetime import date, datetime, timezone

from src.core.registry import Registry
from src.modules.apmatia_ipe.models import (
    ApmatiaIpeObject,
    CalendarEvent,
    CapturedIdea,
    Habit,
    IpeProject,
    IpeTask,
)
from src.modules.apmatia_ipe.module import APMATIA_IPE_MODULE, register
from src.modules.apmatia_ipe.actions import ACTION_DESCRIPTORS
from src.modules.apmatia_ipe.commands import COMMAND_DESCRIPTORS
from src.modules.apmatia_ipe.tools import TOOL_DESCRIPTORS
from src.modules.apmatia_ipe.views import VIEW_DESCRIPTORS


def test_apmatia_ipe_module_registers_module_metadata():
    registry = Registry()

    register(registry)

    assert registry.list_modules() == [APMATIA_IPE_MODULE]
    assert [action.action_id for action in registry.list_actions()] == [action.action_id for action in ACTION_DESCRIPTORS]
    assert [tool.tool_id for tool in registry.list_tools()] == [tool.tool_id for tool in TOOL_DESCRIPTORS]
    assert [command.command_id for command in registry.list_commands()] == [command.command_id for command in COMMAND_DESCRIPTORS]
    assert [view.view_id for view in registry.list_views()] == [view.view_id for view in VIEW_DESCRIPTORS]


def test_apmatia_ipe_data_classes_capture_productivity_state():
    project_idea = CapturedIdea(
        id="idea-1",
        title="Launch productivity assistant",
        tags=("planning", "focus"),
    )

    habit_idea = CapturedIdea(
        id="idea-2",
        title="Daily planning",
    )

    event_idea = CapturedIdea(
        id="idea-3",
        title="Team sync",
        body="Invite Morgan to align on next steps.",
    )

    task = IpeTask(
        id="task-1",
        title="Review weekly priorities",
        project_id="project-1",
        due_at=datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc),
    )

    project = project_idea.convert_to_project(
        project_id="project-1",
        target_on=date(2026, 7, 31),
    )
    habit = habit_idea.convert_to_habit(
        habit_id="habit-1",
        name="Daily planning",
        streak_count=4,
    )
    event = event_idea.convert_to_calendar_event(
        event_id="event-1",
        title="Team sync",
        start_at=datetime(2026, 6, 30, 15, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 30, 15, 30, tzinfo=timezone.utc),
        attendee_ids=("friend-1",),
    )

    assert isinstance(project_idea, ApmatiaIpeObject)
    assert project_idea.id == "idea-1"
    assert project_idea.status == "converted"
    assert project_idea.converted_to_type == "project"
    assert project_idea.converted_to_id == "project-1"
    assert project_idea.converted_at is not None

    assert isinstance(habit_idea, ApmatiaIpeObject)
    assert habit_idea.id == "idea-2"
    assert habit_idea.status == "converted"
    assert habit_idea.converted_to_type == "habit"
    assert habit_idea.converted_to_id == "habit-1"

    assert isinstance(event_idea, ApmatiaIpeObject)
    assert event_idea.id == "idea-3"
    assert event_idea.status == "converted"
    assert event_idea.converted_to_type == "calendar_event"
    assert event_idea.converted_to_id == "event-1"

    assert project.id == "project-1"
    assert project.name == "Launch productivity assistant"
    assert project.description == ""
    assert project.source_idea_id == "idea-1"
    assert project.source_task_id is None

    assert habit.id == "habit-1"
    assert habit.name == "Daily planning"
    assert habit.cadence == "daily"
    assert habit.active is True
    assert habit.streak_count == 4
    assert habit.source_idea_id == "idea-2"

    assert task.id == "task-1"
    assert task.status == "todo"
    assert task.project_id == "project-1"
    assert task.due_at == datetime(2026, 6, 30, 9, 0, tzinfo=timezone.utc)

    task_project = task.convert_to_project(project_id="project-2")
    assert task_project.id == "project-2"
    assert task_project.source_task_id == "task-1"

    assert event.id == "event-1"
    assert event.title == "Team sync"
    assert event.all_day is False
    assert event.description == "Invite Morgan to align on next steps."
    assert event.attendee_ids == ("friend-1",)
    assert event.source_idea_id == "idea-3"


def test_ipe_view_descriptors_define_collection_actions_without_streamlit():
    assert [spec.object_type for spec in VIEW_DESCRIPTORS] == [
        "idea",
        "task",
        "project",
        "habit",
        "calendar_event",
    ]
    for spec in VIEW_DESCRIPTORS:
        assert spec.view_id.endswith(".view")
        assert spec.list_command_id.endswith(".list")
        assert spec.create_command_id.endswith(".create")
        assert spec.edit_command_id.endswith(".edit")
        assert spec.delete_command_id.endswith(".delete")
        assert spec.metadata["ui"] == {"render_mode": "collection", "layout": "table-with-actions"}
