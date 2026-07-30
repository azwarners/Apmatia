from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from .models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewNavigationPaneDescriptor,
    ViewAction,
    ViewBinding,
    ViewComponent,
    ViewDataSource,
    ViewDocument,
    ViewEffect,
    ViewRefreshPolicy,
    ViewStateDefinition,
)
from .validation import validate_view_document


def normalize_view_document(view: Mapping[str, Any] | Any) -> ViewDocument:
    """Normalize a registry view or serialized view contribution into contract version 1."""
    metadata = _view_metadata(view)
    module_id = str(_mapping_value(view, "module_id", default="")).strip()
    declared_presentation = metadata.get("presentation")
    if isinstance(declared_presentation, ViewComponent):
        return _normalize_declared_document(
            view,
            metadata=metadata,
            module_id=module_id,
            presentation=declared_presentation,
        )

    spec = adapt_module_view(view)
    ui = _mapping(metadata.get("ui"))
    contract = _mapping(metadata.get("view_contract"))
    option_sources = {
        str(key): str(value)
        for key, value in _mapping(contract.get("field_option_sources")).items()
        if str(key).strip() and str(value).strip()
    }
    children: list[ViewComponent] = []
    if spec.nav_pane is not None:
        children.append(
            ViewComponent(
                component_id=f"{spec.view_id}:navigation",
                component_type="navigation",
                properties={
                    "title": spec.nav_pane.title,
                    "top_exit_label": spec.nav_pane.top_exit_label,
                    "bottom_exit_label": spec.nav_pane.bottom_exit_label,
                    "empty_state": spec.nav_pane.empty_state,
                    "item_label_key": spec.nav_pane.item_label_key,
                    "item_subtitle_key": spec.nav_pane.item_subtitle_key,
                    "item_detail_key": spec.nav_pane.item_detail_key,
                    "item_value_key": spec.nav_pane.item_value_key,
                },
                binding=ViewBinding(source="items"),
            )
        )
    if spec.render_mode == "form" and spec.edit_form is not None:
        children.append(
            _form_component(
                spec.view_id,
                spec.edit_form,
                component_suffix="form",
                option_sources=option_sources,
            )
        )
    else:
        children.append(
            ViewComponent(
                component_id=f"{spec.view_id}:collection",
                component_type="table" if spec.columns else "collection",
                properties={
                    "item_key": spec.item_key,
                    "empty_state": spec.empty_state,
                    "columns": [
                        {"key": column.key, "label": column.label, "empty_value": column.empty_value}
                        for column in spec.columns
                    ],
                    "item_action_keys": [action.key for action in spec.item_actions],
                },
                binding=ViewBinding(source="items"),
            )
        )
        if spec.create_form is not None:
            children.append(
                _form_component(
                    spec.view_id,
                    spec.create_form,
                    component_suffix="create",
                    option_sources=option_sources,
                )
            )
        if spec.edit_form is not None:
            children.append(
                _form_component(
                    spec.view_id,
                    spec.edit_form,
                    component_suffix="edit",
                    option_sources=option_sources,
                )
            )

    portable_actions = [_portable_action(action) for action in (*spec.view_actions, *spec.item_actions)]
    form_action_keys = {action.key for action in portable_actions}
    for form in (spec.create_form, spec.edit_form):
        if form is None:
            continue
        for action in form.actions:
            if action.key not in form_action_keys:
                portable_actions.append(_portable_form_action(action))
                form_action_keys.add(action.key)
    document = ViewDocument(
        view_id=spec.view_id,
        module_id=module_id,
        title=spec.title,
        description=spec.description,
        presentation=ViewComponent(
            component_id=f"{spec.view_id}:page",
            component_type="page",
            properties={"caption": spec.caption, "render_mode": spec.render_mode},
            children=tuple(children),
        ),
        data_sources=(
            ViewDataSource(
                key="items",
                kind="collection",
                operation=f"module_view_items:{spec.view_id}",
                item_key=spec.item_key,
                empty_text=spec.empty_state,
            ),
            *_parse_portable_data_sources(contract.get("data_sources")),
        ),
        actions=tuple(portable_actions),
        metadata={
            "legacy": True,
            "legacy_layout": str(ui.get("layout") or ""),
            "legacy_renderer": str(ui.get("renderer") or ""),
            "unsupported_reason": spec.unsupported_reason or "",
        },
    )
    return validate_view_document(document)


def _normalize_declared_document(
    view: Mapping[str, Any] | Any,
    *,
    metadata: Mapping[str, Any],
    module_id: str,
    presentation: ViewComponent,
) -> ViewDocument:
    """Build a document from first-class contract objects declared by a module view.

    Contract-ready views declare their renderer-neutral objects directly in metadata.  They must
    not be passed through the legacy ``ui`` adapter because doing so silently discards their
    sources, state, actions, effects, and rich presentation tree.
    """
    presentation = _prepare_declared_presentation(presentation)
    actions: list[ViewAction] = []
    for action in metadata.get("actions") or ():
        if not isinstance(action, ViewAction):
            raise TypeError("Declared view actions must be ViewAction instances")
        payload_command_id = str(action.payload.get("command_id") or "").strip()
        if not action.command_id and payload_command_id:
            action = replace(action, command_id=payload_command_id)
        actions.append(action)

    data_sources = tuple(metadata.get("data_sources") or ())
    state = tuple(metadata.get("state") or ())
    effects = tuple(metadata.get("effects") or ())
    if not all(isinstance(source, ViewDataSource) for source in data_sources):
        raise TypeError("Declared view data sources must be ViewDataSource instances")
    if not all(isinstance(definition, ViewStateDefinition) for definition in state):
        raise TypeError("Declared view state must contain ViewStateDefinition instances")
    if not all(isinstance(effect, ViewEffect) for effect in effects):
        raise TypeError("Declared view effects must be ViewEffect instances")

    refresh_policy = metadata.get("refresh_policy") or ViewRefreshPolicy()
    if not isinstance(refresh_policy, ViewRefreshPolicy):
        raise TypeError("Declared view refresh_policy must be a ViewRefreshPolicy instance")

    contract_keys = {
        "presentation",
        "data_sources",
        "state",
        "actions",
        "effects",
        "refresh_policy",
        "capabilities",
        "required_renderer_capabilities",
    }
    document = ViewDocument(
        view_id=str(_mapping_value(view, "view_id", default="unknown-view")),
        module_id=module_id,
        title=str(_mapping_value(view, "name", default="Untitled view")),
        description=str(_mapping_value(view, "description", default="") or ""),
        presentation=presentation,
        data_sources=data_sources,
        state=state,
        actions=tuple(actions),
        effects=effects,
        refresh_policy=refresh_policy,
        capabilities=tuple(metadata.get("capabilities") or ()),
        required_renderer_capabilities=tuple(metadata.get("required_renderer_capabilities") or ()),
        metadata={key: value for key, value in metadata.items() if key not in contract_keys},
    )
    return validate_view_document(document)


def _prepare_declared_presentation(root: ViewComponent) -> ViewComponent:
    """Canonicalize the concise component declarations used by module-owned views.

    Module declarations use field component IDs as stable field-name shorthand, place table
    bindings on their containing collection, and may reuse a field tuple in create/edit forms.
    The serialized contract is stricter: fields carry an explicit key, tables carry their own
    binding, and component IDs are unique.  Expand that shorthand deterministically here before
    validation and serialization.
    """
    seen_ids: dict[str, int] = {}

    def prepare(component: ViewComponent, inherited_binding: ViewBinding | None = None) -> ViewComponent:
        occurrence = seen_ids.get(component.component_id, 0)
        seen_ids[component.component_id] = occurrence + 1
        component_id = component.component_id if occurrence == 0 else f"{component.component_id}--{occurrence + 1}"

        properties = dict(component.properties)
        if component.component_type == "field" and not str(properties.get("key") or "").strip():
            # ``*-field`` IDs are the stable module declaration shorthand; the serialized
            # contract always receives the resulting explicit semantic key.
            properties["key"] = _field_key_from_component_id(component.component_id)

        binding = component.binding
        if binding is None and properties.get("binding_source"):
            binding = ViewBinding(
                source=str(properties["binding_source"]),
                path=str(properties.get("binding_path") or ""),
            )
        if component.component_type == "table" and binding is None:
            binding = inherited_binding

        child_binding = component.binding or inherited_binding
        children = tuple(prepare(child, child_binding) for child in component.children)
        return replace(
            component,
            component_id=component_id,
            properties=properties,
            binding=binding,
            children=children,
        )

    return prepare(root)


def _field_key_from_component_id(component_id: str) -> str:
    value = component_id.removesuffix("-field")
    for prefix in (
        "alarm-",
        "agent-",
        "host-",
        "pref-",
        "module-",
        "user-",
        "loop-",
        "memory-",
        "tool-",
        "config-",
    ):
        if value.startswith(prefix):
            value = value.removeprefix(prefix)
            break
    return value.replace("-", "_")


def adapt_module_view(
    view: Mapping[str, Any] | Any,
    *,
    items: Sequence[Any] | None = None,
) -> CollectionViewDescriptor:
    """Build the legacy render model without importing an interface package."""
    resolved_items = tuple(items or ())
    metadata = _view_metadata(view)
    ui = _mapping(metadata.get("ui"))
    render_mode = str(ui.get("render_mode") or "collection")
    view_id = str(_mapping_value(view, "view_id", default="unknown-view"))
    name = str(_mapping_value(view, "name", default=view_id))
    description = str(_mapping_value(view, "description", default="") or "")
    caption = str(ui.get("caption") or "")
    plural_label = str(metadata.get("plural_label") or "")
    title = str(ui.get("title") or plural_label or name)
    empty_state = str(ui.get("empty_state") or metadata.get("empty_state") or "No items yet.")
    item_key = str(ui.get("item_key") or "id")
    nav_pane = _parse_navigation_pane(ui.get("nav_pane"))

    if render_mode not in {"collection", "form"}:
        return CollectionViewDescriptor(
            view_id=view_id,
            title=title,
            render_mode=render_mode,
            description=description,
            caption=caption,
            empty_state=empty_state,
            item_key=item_key,
            nav_pane=nav_pane,
            items=resolved_items,
            unsupported_reason=f"Unsupported module view render mode: {render_mode}",
        )

    columns = tuple(_parse_columns(ui.get("columns") or ui.get("fields")))
    if not columns:
        columns = tuple(_columns_from_schema(metadata.get("schema")))
    if not columns:
        columns = _infer_columns(resolved_items, item_key=item_key)
    item_actions = tuple(_parse_actions(ui.get("item_actions")))
    view_actions = tuple(_parse_actions(ui.get("view_actions")))
    fallback_view, fallback_item = _actions_from_commands(ui.get("commands"))
    metadata_view, metadata_item = _actions_from_commands(metadata.get("commands"))
    if not view_actions:
        view_actions = fallback_view or metadata_view
    if not item_actions:
        item_actions = fallback_item or metadata_item

    schema = metadata.get("schema")
    singular = str(metadata.get("singular_label") or "item")
    create_form = _parse_form_descriptor(ui.get("create_form"), default_key="create") or _form_from_schema(
        schema,
        default_key="create",
        default_title=f"Create {singular}",
        field_flag="create",
    )
    raw_edit = ui.get("form") if render_mode == "form" else ui.get("edit_form")
    edit_form = _parse_form_descriptor(raw_edit, default_key="form" if render_mode == "form" else "edit") or _form_from_schema(
        schema,
        default_key="form" if render_mode == "form" else "edit",
        default_title=f"Edit {singular}",
        field_flag="edit",
    )
    return CollectionViewDescriptor(
        view_id=view_id,
        title=title,
        render_mode=render_mode,
        description=description,
        caption=caption,
        empty_state=empty_state,
        item_key=item_key,
        columns=columns,
        item_actions=item_actions,
        view_actions=view_actions,
        create_form=create_form,
        edit_form=edit_form,
        nav_pane=nav_pane,
        items=resolved_items,
    )


def _portable_action(action: ModuleViewActionDescriptor) -> ViewAction:
    command_id = str(action.payload.get("command_id") or "")
    effects = (ViewEffect(effect_type="refresh_source", target="items"),)
    return ViewAction(
        key=action.key,
        intent=action.intent,
        label=action.label,
        scope=action.scope,
        style=action.style,
        command_id=command_id,
        operation="legacy_intent" if not command_id else "",
        payload={key: value for key, value in action.payload.items() if key != "command_id"},
        confirmation=action.confirmation,
        success_effects=effects,
    )


def _portable_form_action(action: ModuleViewFormActionDescriptor) -> ViewAction:
    command_id = str(action.payload.get("command_id") or "")
    return ViewAction(
        key=action.key,
        intent=action.intent,
        label=action.label,
        scope="form",
        style=action.style,
        command_id=command_id,
        operation="legacy_intent" if not command_id else "",
        payload={key: value for key, value in action.payload.items() if key != "command_id"},
    )


def _form_component(
    view_id: str,
    form: ModuleViewFormDescriptor,
    *,
    component_suffix: str,
    option_sources: Mapping[str, str] | None = None,
) -> ViewComponent:
    fields = tuple(
        ViewComponent(
            component_id=f"{view_id}:{component_suffix}:field:{field.key}",
            component_type="field",
            properties={
                "key": field.key,
                "label": field.label,
                "field_type": field.field_type,
                "help_text": field.help_text,
                "placeholder": field.placeholder,
                "default": field.default,
                "required": field.required,
                "min_value": field.min_value,
                "max_value": field.max_value,
                "step": field.step,
                "options": list(field.options),
                "section": field.section,
                **(
                    {"options_source": ViewBinding(source=option_sources[field.key])}
                    if option_sources and field.key in option_sources
                    else {}
                ),
            },
        )
        for field in form.fields
    )
    return ViewComponent(
        component_id=f"{view_id}:{component_suffix}",
        component_type="form",
        properties={
            "key": form.key,
            "title": form.title,
            "description": form.description,
            "submit_label": form.submit_label,
            "cancel_label": form.cancel_label,
            "actions": [
                {"key": action.key, "label": action.label, "intent": action.intent, "style": action.style}
                for action in form.actions
            ],
        },
        children=fields,
    )


def _parse_portable_data_sources(raw: Any) -> tuple[ViewDataSource, ...]:
    sources: list[ViewDataSource] = []
    for entry in _mapping_sequence(raw):
        key = str(entry.get("key") or "").strip()
        operation = str(entry.get("operation") or "").strip()
        if not key or not operation:
            continue
        sources.append(
            ViewDataSource(
                key=key,
                kind=str(entry.get("kind") or "collection").strip() or "collection",
                operation=operation,
                parameters=dict(entry.get("parameters") or {}),
                depends_on=tuple(entry.get("depends_on") or ()),
                projection=tuple(entry.get("projection") or ()),
                item_key=str(entry.get("item_key") or "id"),
                loading_text=str(entry.get("loading_text") or ""),
                empty_text=str(entry.get("empty_text") or ""),
                error_text=str(entry.get("error_text") or ""),
            )
        )
    return tuple(sources)


def _parse_columns(raw: Any) -> list[CollectionColumnDescriptor]:
    result: list[CollectionColumnDescriptor] = []
    for entry in _mapping_sequence(raw):
        key = str(entry.get("key") or entry.get("source") or "").strip()
        if key:
            result.append(
                CollectionColumnDescriptor(
                    key=key,
                    label=str(entry.get("label") or key.replace("_", " ").title()),
                    empty_value=str(entry.get("empty_value") or "-"),
                )
            )
    return result


def _parse_actions(raw: Any) -> list[ModuleViewActionDescriptor]:
    result: list[ModuleViewActionDescriptor] = []
    for entry in _mapping_sequence(raw):
        key = str(entry.get("key") or entry.get("intent") or "").strip()
        if not key:
            continue
        intent = str(entry.get("intent") or key).strip()
        result.append(
            ModuleViewActionDescriptor(
                key=key,
                label=str(entry.get("label") or intent.title()),
                intent=intent,
                scope=str(entry.get("scope") or "item"),
                style=str(entry.get("style") or "secondary"),
                confirmation=bool(entry.get("confirmation", False)),
                payload=dict(entry.get("payload") or {}),
            )
        )
    return result


def _parse_form_descriptor(raw: Any, *, default_key: str) -> ModuleViewFormDescriptor | None:
    if not isinstance(raw, Mapping):
        return None
    return ModuleViewFormDescriptor(
        key=str(raw.get("key") or default_key).strip() or default_key,
        title=str(raw.get("title") or "Form").strip() or "Form",
        description=str(raw.get("description") or "").strip(),
        submit_label=str(raw.get("submit_label") or "Save").strip() or "Save",
        cancel_label=str(raw.get("cancel_label", "Cancel") or "").strip(),
        actions=tuple(_parse_form_actions(raw.get("actions"))),
        fields=tuple(_parse_form_fields(raw.get("fields"))),
    )


def _parse_form_actions(raw: Any) -> list[ModuleViewFormActionDescriptor]:
    result: list[ModuleViewFormActionDescriptor] = []
    for entry in _mapping_sequence(raw):
        key = str(entry.get("key") or entry.get("intent") or "").strip()
        if key:
            intent = str(entry.get("intent") or key).strip()
            result.append(
                ModuleViewFormActionDescriptor(
                    key=key,
                    label=str(entry.get("label") or intent.title()).strip(),
                    intent=intent,
                    style=str(entry.get("style") or "secondary").strip() or "secondary",
                    payload=dict(entry.get("payload") or {}),
                )
            )
    return result


def _parse_form_fields(raw: Any) -> list[ModuleViewFormFieldDescriptor]:
    result: list[ModuleViewFormFieldDescriptor] = []
    for entry in _mapping_sequence(raw):
        key = str(entry.get("key") or "").strip()
        if not key:
            continue
        result.append(_field_descriptor(entry, key))
    return result


def _field_descriptor(entry: Mapping[str, Any], key: str) -> ModuleViewFormFieldDescriptor:
    options = entry.get("options") or ()
    return ModuleViewFormFieldDescriptor(
        key=key,
        label=str(entry.get("label") or key.replace("_", " ").title()).strip(),
        section=str(entry.get("section") or "").strip(),
        field_type=str(entry.get("field_type") or entry.get("type") or entry.get("input") or "text").strip() or "text",
        help_text=str(entry.get("help_text") or entry.get("help") or "").strip(),
        placeholder=str(entry.get("placeholder") or "").strip(),
        default=entry.get("default", ""),
        required=bool(entry.get("required", False)),
        min_value=entry.get("min_value"),
        max_value=entry.get("max_value"),
        step=entry.get("step"),
        options=tuple(options) if _is_sequence(options) else (),
    )


def _parse_navigation_pane(raw: Any) -> ModuleViewNavigationPaneDescriptor | None:
    if not isinstance(raw, Mapping):
        return None
    top_label = str(raw.get("top_exit_label") or "Back to Apmatia").strip() or "Back to Apmatia"
    return ModuleViewNavigationPaneDescriptor(
        title=str(raw.get("title") or "Contacts").strip() or "Contacts",
        top_exit_label=top_label,
        bottom_exit_label=str(raw.get("bottom_exit_label") or top_label).strip() or top_label,
        empty_state=str(raw.get("empty_state") or "No contacts are available yet.").strip(),
        item_label_key=str(raw.get("item_label_key") or "title").strip() or "title",
        item_subtitle_key=str(raw.get("item_subtitle_key") or "chat_preview").strip() or "chat_preview",
        item_detail_key=str(raw.get("item_detail_key") or "last_activity_at").strip() or "last_activity_at",
        item_value_key=str(raw.get("item_value_key") or "id").strip() or "id",
    )


def _columns_from_schema(raw: Any) -> list[CollectionColumnDescriptor]:
    if not isinstance(raw, Mapping):
        return []
    return [
        CollectionColumnDescriptor(
            key=str(entry["key"]),
            label=str(entry.get("label") or str(entry["key"]).replace("_", " ").title()),
            empty_value=str(entry.get("empty_value") or "-"),
        )
        for entry in _mapping_sequence(raw.get("fields"))
        if entry.get("key") and bool(entry.get("list", False))
    ]


def _form_from_schema(
    raw: Any,
    *,
    default_key: str,
    default_title: str,
    field_flag: str,
) -> ModuleViewFormDescriptor | None:
    if not isinstance(raw, Mapping):
        return None
    section_name = "create" if field_flag == "create" else "edit"
    section = _mapping(raw.get(section_name))
    fallback = _mapping(raw.get("create")) if field_flag == "edit" else {}
    raw_fields = [entry for entry in _mapping_sequence(raw.get("fields")) if bool(entry.get(field_flag, False))]
    extra_fields = section.get("extra_fields") or (fallback.get("extra_fields") if field_flag == "edit" else None)
    raw_fields.extend(_mapping_sequence(extra_fields))
    fields = [_field_descriptor(entry, str(entry["key"])) for entry in raw_fields if entry.get("key")]
    if not fields:
        return None
    title = str(section.get("title") or (fallback.get("title") if field_flag == "edit" else "") or default_title).strip()
    if field_flag == "edit":
        title = _edit_title(title)
    return ModuleViewFormDescriptor(
        key=str(section.get("key") or default_key).strip() or default_key,
        title=title,
        description=str(section.get("description") or "").strip(),
        submit_label=str(section.get("submit_label") or "Save").strip() or "Save",
        cancel_label=str(section.get("cancel_label") or "Cancel").strip() or "Cancel",
        actions=tuple(_parse_form_actions(section.get("actions"))),
        fields=tuple(fields),
    )


def _infer_columns(items: Sequence[Any], *, item_key: str) -> tuple[CollectionColumnDescriptor, ...]:
    if not items:
        return ()
    first = items[0]
    values = first if isinstance(first, Mapping) else getattr(first, "__dict__", {})
    if not isinstance(values, Mapping):
        return ()
    keys = [str(key) for key in values if str(key) != item_key and not str(key).startswith("_")][:4]
    return tuple(CollectionColumnDescriptor(key=key, label=key.replace("_", " ").title()) for key in keys)


def _actions_from_commands(raw: Any) -> tuple[tuple[ModuleViewActionDescriptor, ...], tuple[ModuleViewActionDescriptor, ...]]:
    if not isinstance(raw, Mapping):
        return (), ()
    view_actions: list[ModuleViewActionDescriptor] = []
    item_actions: list[ModuleViewActionDescriptor] = []
    for key, label, scope, style in (
        ("create", "Create", "view", "primary"),
        ("edit", "Edit", "item", "secondary"),
        ("delete", "Delete", "item", "secondary"),
    ):
        if not raw.get(key):
            continue
        action = ModuleViewActionDescriptor(
            key=key,
            label=label,
            intent=key,
            scope=scope,
            style=style,
            confirmation=key == "delete",
            payload={"command_id": str(raw[key])},
        )
        (view_actions if scope == "view" else item_actions).append(action)
    return tuple(view_actions), tuple(item_actions)


def _view_metadata(view: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    return _mapping(_mapping_value(view, "metadata", default={}))


def _mapping_value(source: Mapping[str, Any] | Any, key: str, *, default: Any) -> Any:
    return source.get(key, default) if isinstance(source, Mapping) else getattr(source, key, default)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    if not _is_sequence(value):
        return []
    return [entry for entry in value if isinstance(entry, Mapping)]


def _edit_title(title: str) -> str:
    parts = title.split(maxsplit=1)
    if not parts:
        return "Edit"
    if parts[0].lower() in {"create", "capture", "new"}:
        return "Edit" if len(parts) == 1 else f"Edit {parts[1]}"
    return title if title.lower().startswith("edit ") else f"Edit {title}".strip()
