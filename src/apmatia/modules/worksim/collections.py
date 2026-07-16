"""Shared collection metadata for the Apmatia Worksim module."""

from __future__ import annotations

from dataclasses import dataclass

from apmatia.core.module_view_schema import build_collection_view_schema

from .models import WorksimOrgChartEntry


@dataclass(frozen=True, slots=True)
class WorksimOrgChartViewSpec:
    object_type: str
    singular_label: str
    plural_label: str
    description: str
    empty_state: str
    schema: dict[str, object] | None = None

    @property
    def action_id(self) -> str:
        return f"worksim.{self.object_type}"

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
        return {
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
            "ui": {
                "render_mode": "collection",
                "layout": "table-with-actions",
                "title": "Apmatia Workplace Org Chart",
                "caption": "The user is the root by default and agents can branch beneath it.",
            },
            "schema": dict(self.schema or {}),
        }


ORG_CHART_VIEW_SPECS: tuple[WorksimOrgChartViewSpec, ...] = (
    WorksimOrgChartViewSpec(
        object_type="org_chart_node",
        singular_label="Org Chart Node",
        plural_label="Org Chart Nodes",
        description="A persistent workplace wiki where the user is the root and agents branch beneath it.",
        empty_state="The org chart will appear here once the root wiki is created.",
        schema=build_collection_view_schema(
            WorksimOrgChartEntry,
            list_fields=("path", "title", "node_type", "parent_id", "sort_order"),
            create_fields=("parent_id", "node_type", "title", "body", "sort_order"),
            edit_fields=("parent_id", "node_type", "title", "body", "sort_order"),
            field_overrides={
                "id": {"hidden": True},
                "wiki_id": {"hidden": True},
                "depth": {"hidden": True},
                "owner_user_id": {"hidden": True},
                "owner_agent_id": {"hidden": True},
                "is_root": {"hidden": True},
                "path": {
                    "label": "Org Path",
                },
                "parent_id": {
                    "label": "Parent Node",
                    "help_text": "Leave blank to use the user root on create. Use root to move a node back to the root on edit.",
                    "placeholder": "root",
                },
                "node_type": {
                    "label": "Node Type",
                    "field_type": "select",
                    "options": ("branch", "leaf"),
                    "default": "branch",
                },
                "title": {
                    "label": "Title",
                    "placeholder": "e.g. Engineering Lead",
                },
                "body": {
                    "label": "Notes",
                    "field_type": "textarea",
                    "placeholder": "Optional role notes, responsibilities, or team details.",
                },
                "sort_order": {
                    "label": "Order",
                    "default": 0,
                },
            },
        ),
    ),
)
