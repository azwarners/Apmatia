from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleViewFormDescriptor:
    key: str
    title: str
    description: str = ""
    submit_label: str = "Save"
    cancel_label: str = "Cancel"
    fields: tuple[ModuleViewFormFieldDescriptor, ...] = ()


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
    items: tuple[Any, ...] = ()
    unsupported_reason: str | None = None

    @property
    def is_supported(self) -> bool:
        return self.unsupported_reason is None


ModuleViewRenderModel = CollectionViewDescriptor
