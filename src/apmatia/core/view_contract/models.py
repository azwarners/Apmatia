from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any


VIEW_CONTRACT_VERSION = 1
SUPPORTED_COMPONENT_TYPES = frozenset(
    {
        "page",
        "stack",
        "columns",
        "tabs",
        "panel",
        "card",
        "collection",
        "table",
        "form",
        "field",
        "text",
        "markdown",
        "status",
        "notice",
        "actions",
        "navigation",
        "detail",
        "timeline",
        "message",
        "composer",
        "terminal",
        "progress",
        "checklist",
        "tree",
        "expander",
    }
)
SUPPORTED_STATE_SCOPES = frozenset({"event", "view", "session", "server"})
SUPPORTED_STATE_VALUE_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "date", "time", "datetime", "object", "array"}
)
SUPPORTED_DATA_SOURCE_KINDS = frozenset({"singleton", "collection", "stream", "tree"})
SUPPORTED_REFRESH_MODES = frozenset({"manual", "on_intent", "poll", "stream"})
SUPPORTED_UPDATE_STRATEGIES = frozenset({"replace", "append"})
SUPPORTED_ACTION_SCOPES = frozenset({"view", "item", "selection", "form", "message", "navigation"})
SUPPORTED_FIELD_TYPES = frozenset(
    {"text", "textarea", "number", "checkbox", "color", "slider", "select", "multiselect", "date", "time", "datetime", "password", "hidden", "file"}
)
SUPPORTED_CONDITION_OPERATORS = frozenset(
    {"all", "any", "not", "equals", "not_equals", "in", "not_in", "exists", "truthy", "falsy", "gt", "gte", "lt", "lte"}
)
SUPPORTED_EFFECT_TYPES = frozenset(
    {
        "refresh_source",
        "refresh_view",
        "set_state",
        "clear_state",
        "select_item",
        "navigate",
        "open_panel",
        "close_panel",
        "show_notification",
        "start_polling",
        "stop_polling",
        "download",
    }
)


@dataclass(frozen=True, slots=True)
class ViewBinding:
    source: str
    path: str = ""
    default: Any = None


@dataclass(frozen=True, slots=True)
class ViewCondition:
    operator: str
    operands: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewComponent:
    component_id: str
    component_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    binding: ViewBinding | None = None
    visible_when: ViewCondition | None = None
    action_keys: tuple[str, ...] = ()
    children: tuple["ViewComponent", ...] = ()


@dataclass(frozen=True, slots=True)
class ViewRefreshPolicy:
    mode: str = "manual"
    interval_seconds: float | None = None
    cursor_key: str = ""
    generation_key: str = ""
    update_strategy: str = "replace"
    reject_stale: bool = True
    stop_when: ViewCondition | None = None


@dataclass(frozen=True, slots=True)
class ViewDataSource:
    key: str
    kind: str = "collection"
    operation: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    projection: tuple[str, ...] = ()
    item_key: str = "id"
    loading_text: str = ""
    empty_text: str = ""
    error_text: str = ""
    refresh: ViewRefreshPolicy = field(default_factory=ViewRefreshPolicy)


@dataclass(frozen=True, slots=True)
class ViewStateDefinition:
    key: str
    value_type: str = "string"
    default: Any = None
    scope: str = "view"
    reset_on: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewEffect:
    effect_type: str
    target: str = ""
    value: Any = None
    source: str = ""


@dataclass(frozen=True, slots=True)
class ViewAction:
    key: str
    intent: str
    label: str
    scope: str = "item"
    style: str = "secondary"
    command_id: str = ""
    operation: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    confirmation: bool = False
    prevent_duplicate_submission: bool = True
    enabled_when: ViewCondition | None = None
    success_effects: tuple[ViewEffect, ...] = ()
    failure_effects: tuple[ViewEffect, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewDocument:
    view_id: str
    module_id: str
    title: str
    schema_version: int = VIEW_CONTRACT_VERSION
    description: str = ""
    presentation: ViewComponent | None = None
    data_sources: tuple[ViewDataSource, ...] = ()
    state: tuple[ViewStateDefinition, ...] = ()
    actions: tuple[ViewAction, ...] = ()
    effects: tuple[ViewEffect, ...] = ()
    refresh_policy: ViewRefreshPolicy = field(default_factory=ViewRefreshPolicy)
    capabilities: tuple[str, ...] = ()
    required_renderer_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_safe(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return str(value)


# Compatibility render model used by the existing Streamlit renderer. These types are neutral and
# remain intentionally separate from the richer serialized document above during migration.
@dataclass(frozen=True, slots=True)
class CollectionColumnDescriptor:
    key: str
    label: str
    empty_value: str = "-"


@dataclass(frozen=True, slots=True)
class ModuleViewActionDescriptor:
    key: str
    label: str
    intent: str
    scope: str = "item"
    style: str = "secondary"
    confirmation: bool = False
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModuleViewFormActionDescriptor:
    key: str
    label: str
    intent: str
    style: str = "secondary"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModuleViewIntent:
    view_id: str
    intent: str
    action_key: str
    scope: str
    item_id: str | None = None
    item: Any | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModuleViewFormFieldDescriptor:
    key: str
    label: str
    field_type: str = "text"
    help_text: str = ""
    placeholder: str = ""
    default: Any = ""
    required: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    step: int | float | None = None
    options: tuple[Any, ...] = ()
    section: str = ""


@dataclass(frozen=True, slots=True)
class ModuleViewFormDescriptor:
    key: str
    title: str
    description: str = ""
    submit_label: str = "Save"
    cancel_label: str = "Cancel"
    actions: tuple[ModuleViewFormActionDescriptor, ...] = ()
    fields: tuple[ModuleViewFormFieldDescriptor, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleViewNavigationPaneDescriptor:
    title: str
    top_exit_label: str = "Back to Apmatia"
    bottom_exit_label: str = "Back to Apmatia"
    empty_state: str = "No contacts are available yet."
    item_label_key: str = "title"
    item_subtitle_key: str = "chat_preview"
    item_detail_key: str = "last_activity_at"
    item_value_key: str = "id"


@dataclass(frozen=True, slots=True)
class CollectionViewDescriptor:
    view_id: str
    title: str
    description: str = ""
    caption: str = ""
    empty_state: str = "No items yet."
    item_key: str = "id"
    columns: tuple[CollectionColumnDescriptor, ...] = ()
    item_actions: tuple[ModuleViewActionDescriptor, ...] = ()
    view_actions: tuple[ModuleViewActionDescriptor, ...] = ()
    create_form: ModuleViewFormDescriptor | None = None
    edit_form: ModuleViewFormDescriptor | None = None
    nav_pane: ModuleViewNavigationPaneDescriptor | None = None
    items: tuple[Any, ...] = ()
    unsupported_reason: str | None = None
    render_mode: str = "collection"

    @property
    def is_supported(self) -> bool:
        return self.unsupported_reason is None


ModuleViewRenderModel = CollectionViewDescriptor
