from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from apmatia.core.registry import ViewContribution
from apmatia.interfaces.streamlit.module_views.models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewNavigationPaneDescriptor,
)


def adapt_module_view(
    view: ViewContribution | Mapping[str, Any],
    *,
    items: Sequence[Any] | None = None,
) -> CollectionViewDescriptor:
    resolved_items = tuple(items or ())
    metadata = _view_metadata(view)
    ui = _mapping_value(metadata, "ui", default={})
    render_mode = str(_mapping_value(ui, "render_mode", default="collection") or "collection")

    view_id = str(_mapping_value(view, "view_id", default="unknown-view"))
    name = str(_mapping_value(view, "name", default=view_id))
    description = str(_mapping_value(view, "description", default="") or "")
    caption = str(_mapping_value(ui, "caption", default="") or "")
    plural_label = str(_mapping_value(metadata, "plural_label", default="") or "")
    title = str(_mapping_value(ui, "title", default=plural_label or name) or plural_label or name)
    empty_state = str(
        _mapping_value(
            ui,
            "empty_state",
            default=_mapping_value(metadata, "empty_state", default="No items yet."),
        )
        or _mapping_value(metadata, "empty_state", default="No items yet.")
        or "No items yet."
    )
    item_key = str(_mapping_value(ui, "item_key", default="id") or "id")

    if render_mode != "collection":
        return CollectionViewDescriptor(
            view_id=view_id,
            title=title,
            description=description,
            caption=caption,
            empty_state=empty_state,
            item_key=item_key,
            nav_pane=_parse_navigation_pane(_mapping_value(ui, "nav_pane", default=None)),
            items=resolved_items,
            unsupported_reason=f"Unsupported module view render mode: {render_mode}",
        )

    columns = tuple(_parse_columns(_mapping_value(ui, "columns", default=())))
    if not columns:
        columns = tuple(_parse_columns(_mapping_value(ui, "fields", default=())))
    if not columns:
        columns = tuple(_columns_from_schema(_mapping_value(metadata, "schema", default=None)))
    if not columns:
        columns = _infer_columns(resolved_items, item_key=item_key)
    item_actions = tuple(_parse_actions(_mapping_value(ui, "item_actions", default=())))
    view_actions = tuple(_parse_actions(_mapping_value(ui, "view_actions", default=())))
    if not item_actions or not view_actions:
        fallback_commands = _mapping_value(ui, "commands", default={})
        fallback_view_actions, fallback_item_actions = _actions_from_commands(fallback_commands)
        if not fallback_view_actions or not fallback_item_actions:
            metadata_fallback_view_actions, metadata_fallback_item_actions = _actions_from_commands(
                _mapping_value(metadata, "commands", default={})
            )
            if not fallback_view_actions:
                fallback_view_actions = metadata_fallback_view_actions
            if not fallback_item_actions:
                fallback_item_actions = metadata_fallback_item_actions
        if not view_actions:
            view_actions = fallback_view_actions
        if not item_actions:
            item_actions = fallback_item_actions

    return CollectionViewDescriptor(
        view_id=view_id,
        title=title,
        description=description,
        caption=caption,
        empty_state=empty_state,
        item_key=item_key,
        columns=columns,
        item_actions=item_actions,
        view_actions=view_actions,
        create_form=(
            _parse_form_descriptor(_mapping_value(ui, "create_form", default=None), default_key="create")
            or _form_from_schema(
                _mapping_value(metadata, "schema", default=None),
                default_key="create",
                default_title=f"Create {str(_mapping_value(metadata, 'singular_label', default='item') or 'item')}",
                field_flag="create",
            )
        ),
        edit_form=(
            _parse_form_descriptor(_mapping_value(ui, "edit_form", default=None), default_key="edit")
            or _form_from_schema(
                _mapping_value(metadata, "schema", default=None),
                default_key="edit",
                default_title=f"Edit {str(_mapping_value(metadata, 'singular_label', default='item') or 'item')}",
                field_flag="edit",
            )
        ),
        nav_pane=_parse_navigation_pane(_mapping_value(ui, "nav_pane", default=None)),
        items=resolved_items,
    )


def _view_metadata(view: ViewContribution | Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = _mapping_value(view, "metadata", default={})
    return metadata if isinstance(metadata, Mapping) else {}


def _mapping_value(source: Mapping[str, Any] | Any, key: str, *, default: Any) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _parse_columns(raw_columns: Any) -> list[CollectionColumnDescriptor]:
    if not isinstance(raw_columns, Sequence) or isinstance(raw_columns, (str, bytes)):
        return []

    columns: list[CollectionColumnDescriptor] = []
    for entry in raw_columns:
        if not isinstance(entry, Mapping):
            continue
        key = str(entry.get("key") or entry.get("source") or "").strip()
        if not key:
            continue
        label = str(entry.get("label") or key.replace("_", " ").title())
        empty_value = str(entry.get("empty_value") or "-")
        columns.append(CollectionColumnDescriptor(key=key, label=label, empty_value=empty_value))
    return columns


def _parse_actions(raw_actions: Any) -> list[ModuleViewActionDescriptor]:
    if not isinstance(raw_actions, Sequence) or isinstance(raw_actions, (str, bytes)):
        return []

    actions: list[ModuleViewActionDescriptor] = []
    for entry in raw_actions:
        if not isinstance(entry, Mapping):
            continue
        key = str(entry.get("key") or entry.get("intent") or "").strip()
        intent = str(entry.get("intent") or key).strip()
        label = str(entry.get("label") or intent.title())
        scope = str(entry.get("scope") or "item")
        style = str(entry.get("style") or "secondary")
        confirmation = bool(entry.get("confirmation", False))
        payload = dict(entry.get("payload") or {})
        if not key:
            continue
        actions.append(
            ModuleViewActionDescriptor(
                key=key,
                label=label,
                intent=intent,
                scope=scope,
                style=style,
                confirmation=confirmation,
                payload=payload,
            )
        )
    return actions


def _parse_form_descriptor(raw_form: Any, *, default_key: str) -> ModuleViewFormDescriptor | None:
    if not isinstance(raw_form, Mapping):
        return None

    key = str(raw_form.get("key") or default_key).strip() or default_key
    title = str(raw_form.get("title") or "Form").strip() or "Form"
    description = str(raw_form.get("description") or "").strip()
    submit_label = str(raw_form.get("submit_label") or "Save").strip() or "Save"
    cancel_label = str(raw_form.get("cancel_label") or "Cancel").strip() or "Cancel"
    actions = tuple(_parse_form_actions(raw_form.get("actions")))
    fields = tuple(_parse_form_fields(raw_form.get("fields")))
    return ModuleViewFormDescriptor(
        key=key,
        title=title,
        description=description,
        submit_label=submit_label,
        cancel_label=cancel_label,
        actions=actions,
        fields=fields,
    )


def _parse_form_actions(raw_actions: Any) -> list[ModuleViewFormActionDescriptor]:
    if not isinstance(raw_actions, Sequence) or isinstance(raw_actions, (str, bytes)):
        return []

    actions: list[ModuleViewFormActionDescriptor] = []
    for entry in raw_actions:
        if not isinstance(entry, Mapping):
            continue
        key = str(entry.get("key") or entry.get("intent") or "").strip()
        intent = str(entry.get("intent") or key).strip()
        label = str(entry.get("label") or intent.title()).strip()
        style = str(entry.get("style") or "secondary").strip() or "secondary"
        payload = dict(entry.get("payload") or {})
        if not key:
            continue
        actions.append(
            ModuleViewFormActionDescriptor(
                key=key,
                label=label,
                intent=intent,
                style=style,
                payload=payload,
            )
        )
    return actions


def _parse_form_fields(raw_fields: Any) -> list[ModuleViewFormFieldDescriptor]:
    if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes)):
        return []

    fields: list[ModuleViewFormFieldDescriptor] = []
    for entry in raw_fields:
        if not isinstance(entry, Mapping):
            continue
        key = str(entry.get("key") or "").strip()
        if not key:
            continue
        label = str(entry.get("label") or key.replace("_", " ").title()).strip()
        field_type = str(entry.get("field_type") or entry.get("type") or "text").strip() or "text"
        help_text = str(entry.get("help_text") or entry.get("help") or "").strip()
        placeholder = str(entry.get("placeholder") or "").strip()
        default = entry.get("default", "")
        required = bool(entry.get("required", False))
        min_value = entry.get("min_value")
        max_value = entry.get("max_value")
        step = entry.get("step")
        raw_options = entry.get("options") or ()
        options = (
            tuple(str(option) for option in raw_options)
            if isinstance(raw_options, Sequence) and not isinstance(raw_options, (str, bytes))
            else ()
        )
        fields.append(
            ModuleViewFormFieldDescriptor(
                key=key,
                label=label,
                field_type=field_type,
                help_text=help_text,
                placeholder=placeholder,
                default=default,
                required=required,
                min_value=min_value,
                max_value=max_value,
                step=step,
                options=options,
            )
        )
    return fields


def _parse_navigation_pane(raw_nav_pane: Any) -> ModuleViewNavigationPaneDescriptor | None:
    if not isinstance(raw_nav_pane, Mapping):
        return None

    title = str(raw_nav_pane.get("title") or "Contacts").strip() or "Contacts"
    top_exit_label = str(raw_nav_pane.get("top_exit_label") or "Back to Apmatia").strip() or "Back to Apmatia"
    bottom_exit_label = str(raw_nav_pane.get("bottom_exit_label") or top_exit_label).strip() or top_exit_label
    empty_state = str(raw_nav_pane.get("empty_state") or "No contacts are available yet.").strip() or "No contacts are available yet."
    item_label_key = str(raw_nav_pane.get("item_label_key") or "title").strip() or "title"
    item_subtitle_key = str(raw_nav_pane.get("item_subtitle_key") or "chat_preview").strip() or "chat_preview"
    item_detail_key = str(raw_nav_pane.get("item_detail_key") or "last_activity_at").strip() or "last_activity_at"
    item_value_key = str(raw_nav_pane.get("item_value_key") or "id").strip() or "id"
    return ModuleViewNavigationPaneDescriptor(
        title=title,
        top_exit_label=top_exit_label,
        bottom_exit_label=bottom_exit_label,
        empty_state=empty_state,
        item_label_key=item_label_key,
        item_subtitle_key=item_subtitle_key,
        item_detail_key=item_detail_key,
        item_value_key=item_value_key,
    )


def _columns_from_schema(raw_schema: Any) -> list[CollectionColumnDescriptor]:
    if not isinstance(raw_schema, Mapping):
        return []

    raw_fields = raw_schema.get("fields")
    if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes)):
        return []

    columns: list[CollectionColumnDescriptor] = []
    for entry in raw_fields:
        if not isinstance(entry, Mapping) or not bool(entry.get("list", False)):
            continue
        key = str(entry.get("key") or "").strip()
        if not key:
            continue
        columns.append(
            CollectionColumnDescriptor(
                key=key,
                label=str(entry.get("label") or key.replace("_", " ").title()),
                empty_value=str(entry.get("empty_value") or "-"),
            )
        )
    return columns


def _form_from_schema(
    raw_schema: Any,
    *,
    default_key: str,
    default_title: str,
    field_flag: str,
) -> ModuleViewFormDescriptor | None:
    if not isinstance(raw_schema, Mapping):
        return None

    raw_fields = raw_schema.get("fields")
    if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes)):
        return None

    fields: list[ModuleViewFormFieldDescriptor] = []
    for entry in raw_fields:
        if not isinstance(entry, Mapping) or not bool(entry.get(field_flag, False)):
            continue
        key = str(entry.get("key") or "").strip()
        if not key:
            continue
        options = entry.get("options") or ()
        parsed_options = (
            tuple(str(option) for option in options)
            if isinstance(options, Sequence) and not isinstance(options, (str, bytes))
            else ()
        )
        fields.append(
            ModuleViewFormFieldDescriptor(
                key=key,
                label=str(entry.get("label") or key.replace("_", " ").title()),
                field_type=str(entry.get("field_type") or entry.get("input") or "text"),
                help_text=str(entry.get("help_text") or ""),
                placeholder=str(entry.get("placeholder") or ""),
                default=entry.get("default", ""),
                required=bool(entry.get("required", False)),
                min_value=entry.get("min_value"),
                max_value=entry.get("max_value"),
                step=entry.get("step"),
                options=parsed_options,
            )
        )

    section_key = "create" if field_flag == "create" else "edit"
    section_metadata = raw_schema.get(section_key)
    create_section = section_metadata if isinstance(section_metadata, Mapping) else {}
    fallback_section = raw_schema.get("create") if field_flag == "edit" else None
    fallback_section = fallback_section if isinstance(fallback_section, Mapping) else {}
    if field_flag == "edit":
        extra_fields = create_section.get("extra_fields") or fallback_section.get("extra_fields")
    else:
        extra_fields = create_section.get("extra_fields")
    if isinstance(extra_fields, Sequence) and not isinstance(extra_fields, (str, bytes)):
        for entry in extra_fields:
            if not isinstance(entry, Mapping):
                continue
            key = str(entry.get("key") or "").strip()
            if not key:
                continue
            options = entry.get("options") or ()
            parsed_options = (
                tuple(str(option) for option in options)
                if isinstance(options, Sequence) and not isinstance(options, (str, bytes))
                else ()
            )
            fields.append(
                ModuleViewFormFieldDescriptor(
                    key=key,
                    label=str(entry.get("label") or key.replace("_", " ").title()),
                    field_type=str(entry.get("field_type") or entry.get("input") or "text"),
                    help_text=str(entry.get("help_text") or ""),
                    placeholder=str(entry.get("placeholder") or ""),
                    default=entry.get("default", ""),
                    required=bool(entry.get("required", False)),
                    min_value=entry.get("min_value"),
                    max_value=entry.get("max_value"),
                    step=entry.get("step"),
                    options=parsed_options,
                )
            )

    if not fields:
        return None
    title = str(
        create_section.get("title")
        or (fallback_section.get("title") if field_flag == "edit" else "")
        or default_title
    ).strip() or default_title
    if field_flag == "edit":
        title = _edit_title(title)
    return ModuleViewFormDescriptor(
        key=str(create_section.get("key") or default_key).strip() or default_key,
        title=title,
        description=str(create_section.get("description") or "").strip(),
        submit_label=str(create_section.get("submit_label") or "Save").strip() or "Save",
        cancel_label=str(create_section.get("cancel_label") or "Cancel").strip() or "Cancel",
        actions=tuple(_parse_form_actions(create_section.get("actions"))),
        fields=tuple(fields),
    )


def _infer_columns(items: Sequence[Any], *, item_key: str) -> tuple[CollectionColumnDescriptor, ...]:
    if not items:
        return ()

    first_item = items[0]
    if isinstance(first_item, Mapping):
        keys = [str(key) for key in first_item.keys() if str(key) != item_key]
        return tuple(CollectionColumnDescriptor(key=key, label=key.replace("_", " ").title()) for key in keys[:4])

    item_dict = getattr(first_item, "__dict__", None)
    if isinstance(item_dict, dict):
        keys = [str(key) for key in item_dict if str(key) != item_key and not str(key).startswith("_")]
        return tuple(CollectionColumnDescriptor(key=key, label=key.replace("_", " ").title()) for key in keys[:4])

    return ()


def _actions_from_commands(raw_commands: Any) -> tuple[tuple[ModuleViewActionDescriptor, ...], tuple[ModuleViewActionDescriptor, ...]]:
    if not isinstance(raw_commands, Mapping):
        return (), ()

    view_actions: list[ModuleViewActionDescriptor] = []
    item_actions: list[ModuleViewActionDescriptor] = []
    action_specs = (
        ("create", "Create", "view", "primary"),
        ("edit", "Edit", "item", "secondary"),
        ("delete", "Delete", "item", "secondary"),
    )
    for key, label, scope, style in action_specs:
        command_id = raw_commands.get(key)
        if not command_id:
            continue
        descriptor = ModuleViewActionDescriptor(
            key=key,
            label=label,
            intent=key,
            scope=scope,
            style=style,
            confirmation=key == "delete",
            payload={"command_id": str(command_id)},
        )
        if scope == "view":
            view_actions.append(descriptor)
        else:
            item_actions.append(descriptor)
    return tuple(view_actions), tuple(item_actions)


def _edit_title(title: str) -> str:
    parts = title.split(maxsplit=1)
    if not parts:
        return "Edit"
    if parts[0].lower() in {"create", "capture", "new"}:
        if len(parts) == 1:
            return "Edit"
        return f"Edit {parts[1]}"
    if title.lower().startswith("edit "):
        return title
    return f"Edit {title}".strip()
