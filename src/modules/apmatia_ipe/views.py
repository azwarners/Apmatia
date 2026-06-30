"""View descriptors for the Apmatia IPE module."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.module_view_schema import build_collection_view_schema
from src.core.registry import ViewContribution

from .models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask


@dataclass(frozen=True, slots=True)
class IpeCollectionViewSpec:
    object_type: str
    singular_label: str
    plural_label: str
    description: str
    empty_state: str
    schema: dict[str, object] | None = None

    @property
    def action_id(self) -> str:
        return f"apmatia_ipe.{self.object_type}"

    @property
    def view_id(self) -> str:
        return f"{self.action_id}.view"

    @property
    def list_command_id(self) -> str:
        return f"{self.action_id}.list"

    @property
    def create_command_id(self) -> str:
        return f"{self.action_id}.create"

    @property
    def edit_command_id(self) -> str:
        return f"{self.action_id}.edit"

    @property
    def delete_command_id(self) -> str:
        return f"{self.action_id}.delete"

    @property
    def metadata(self) -> dict[str, object]:
        ui: dict[str, object] = {
            "render_mode": "collection",
            "layout": "table-with-actions",
        }

        metadata = {
            "object_type": self.object_type,
            "singular_label": self.singular_label,
            "plural_label": self.plural_label,
            "empty_state": self.empty_state,
            "commands": {
                "list": self.list_command_id,
                "create": self.create_command_id,
                "edit": self.edit_command_id,
                "delete": self.delete_command_id,
            },
            "ui": ui,
        }
        if self.schema:
            metadata["schema"] = dict(self.schema)
        return metadata


IPE_COLLECTION_VIEW_SPECS: tuple[IpeCollectionViewSpec, ...] = (
    IpeCollectionViewSpec(
        object_type="idea",
        singular_label="Idea",
        plural_label="Ideas",
        description="Capture, review, and convert loose thoughts into structured work.",
        empty_state="No captured ideas yet.",
        schema=build_collection_view_schema(
            CapturedIdea,
            list_fields=("title", "body", "source", "captured_at"),
            create_fields=("title", "body", "source", "tags"),
            create={
                "key": "create_idea",
                "title": "Capture idea",
                "description": "Quickly capture an idea so you can review and organize it later.",
                "submit_label": "Save idea",
                "cancel_label": "Cancel",
            },
            field_overrides={
                "id": {"hidden": True},
                "owner_user_id": {"hidden": True},
                "owner_group_id": {"hidden": True},
                "mode": {"hidden": True},
                "created_at": {"hidden": True},
                "updated_at": {"hidden": True},
                "status": {"hidden": True},
                "source_idea_id": {"hidden": True},
                "converted_to_type": {"hidden": True},
                "converted_to_id": {"hidden": True},
                "converted_at": {"hidden": True},
                "title": {
                    "placeholder": "Short summary of the idea",
                },
                "body": {
                    "label": "Details",
                    "field_type": "textarea",
                    "placeholder": "Write the idea, context, and any next thoughts here.",
                },
                "source": {
                    "placeholder": "manual",
                },
                "tags": {
                    "field_type": "text",
                    "placeholder": "comma, separated, tags",
                },
                "captured_at": {
                    "label": "Captured",
                },
            },
        ),
    ),
    IpeCollectionViewSpec(
        object_type="task",
        singular_label="Task",
        plural_label="Tasks",
        description="Track actionable work that should be done next.",
        empty_state="No tasks yet.",
        schema=build_collection_view_schema(
            IpeTask,
            list_fields=("title", "status", "priority", "due_at"),
            field_overrides={
                "due_at": {"label": "Due"},
            },
        ),
    ),
    IpeCollectionViewSpec(
        object_type="project",
        singular_label="Project",
        plural_label="Projects",
        description="Keep multi-step efforts organized and visible.",
        empty_state="No projects yet.",
        schema=build_collection_view_schema(
            IpeProject,
            list_fields=("name", "description", "started_on", "target_on"),
            field_overrides={
                "started_on": {"label": "Started"},
                "target_on": {"label": "Target"},
            },
        ),
    ),
    IpeCollectionViewSpec(
        object_type="habit",
        singular_label="Habit",
        plural_label="Habits",
        description="Monitor repeating routines and streaks.",
        empty_state="No habits yet.",
        schema=build_collection_view_schema(
            Habit,
            list_fields=("name", "cadence", "target_count", "streak_count"),
            field_overrides={
                "target_count": {"label": "Target"},
                "streak_count": {"label": "Streak"},
            },
        ),
    ),
    IpeCollectionViewSpec(
        object_type="calendar_event",
        singular_label="Calendar Event",
        plural_label="Calendar Events",
        description="Schedule commitments, meetings, and time blocks.",
        empty_state="No calendar events yet.",
        schema=build_collection_view_schema(
            CalendarEvent,
            list_fields=("title", "start_at", "end_at", "location"),
            field_overrides={
                "start_at": {"label": "Start"},
                "end_at": {"label": "End"},
                "all_day": {"hidden": True},
                "attendee_ids": {"hidden": True},
            },
        ),
    ),
)

VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = tuple(
    ViewContribution(
        module_id="apmatia_ipe",
        action_id=spec.action_id,
        view_id=spec.view_id,
        name=f"{spec.plural_label} View",
        description=spec.description,
        metadata=spec.metadata,
    )
    for spec in IPE_COLLECTION_VIEW_SPECS
)
