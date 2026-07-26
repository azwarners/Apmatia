from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.core.models import utc_now

from .models import CalendarEvent, CapturedIdea, Habit, IpeProject, IpeTask
from .services import ApmatiaIpeService


class ApmatiaIpeModuleViewProvider:
    def __init__(
        self,
        service: ApmatiaIpeService | None = None,
        service_factory: Callable[[], ApmatiaIpeService] | None = None,
    ):
        self._service = service
        self._service_factory = service_factory

    @property
    def service(self) -> ApmatiaIpeService:
        if self._service is None:
            if self._service_factory is None:
                raise ValueError("Apmatia IPE module view provider is missing a service factory.")
            self._service = self._service_factory()
        return self._service

    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        items = [item for item in self._list_objects(object_type) if _is_visible(item, context=context)]
        items.sort(key=_sort_key, reverse=True)
        return [_serialize_object(object_type, item) for item in items]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)

        if verb == "create":
            return self._create_object(object_type, payload=payload, context=context)
        if verb == "delete":
            return self._delete_object(object_type, payload=payload, context=context)
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        raise ValueError(f"Unsupported module command verb for now: {verb}")

    def _list_objects(self, object_type: str) -> list[Any]:
        if object_type == "idea":
            return list(self.service.ideas.list_all())
        if object_type == "task":
            return list(self.service.tasks.list_all())
        if object_type == "project":
            return list(self.service.projects.list_all())
        if object_type == "habit":
            return list(self.service.habits.list_all())
        if object_type == "calendar_event":
            return list(self.service.calendar_events.list_all())
        raise ValueError(f"Unsupported module object type: {object_type}")

    def _create_object(
        self,
        object_type: str,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        if object_type != "idea":
            raise ValueError(f"Create is not available for {object_type} yet.")

        title = str(payload.get("title") or "").strip()
        body = str(payload.get("body") or "").strip()
        if not title and not body:
            raise ValueError("Provide an idea title or description.")

        idea = CapturedIdea(
            title=title or _derive_title(body),
            body=body,
            source=str(payload.get("source") or "manual").strip() or "manual",
            tags=_parse_tags(payload.get("tags")),
            captured_at=utc_now(),
        )
        idea.owner_user_id = context.user_id

        created_id = self.service.ideas.create(idea)
        created = replace(idea, id=created_id)
        return {
            "status": "created",
            "item": _serialize_object("idea", created),
        }

    def _delete_object(
        self,
        object_type: str,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        item_id = _require_int(payload.get("item_id"))
        target = _get_object(self.service, object_type, item_id)
        if target is None:
            raise ValueError(f"{object_type.replace('_', ' ').title()} not found: {item_id}")
        if not _is_visible(target, context=context):
            raise ValueError("You do not have access to that item.")

        deleted = _delete_object(self.service, object_type, item_id)
        return {
            "status": "deleted" if deleted else "not_found",
            "item_id": item_id,
            "deleted": bool(deleted),
        }


def _view_from_command(command: CommandContribution) -> ViewContribution:
    view_id = str(command.metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=str(command.metadata.get("collection_view_id") or command.module_id).removesuffix(".view"),
        view_id=view_id,
        name=command.name,
        description=command.description,
        metadata=dict(command.metadata or {}),
    )


def _object_type(metadata: Mapping[str, Any]) -> str:
    object_type = str(metadata.get("object_type") or "").strip()
    if not object_type:
        raise ValueError("Module metadata is missing object_type.")
    return object_type


def _command_verb(command_id: str) -> str:
    parts = [part for part in str(command_id).split(".") if part]
    return "" if not parts else parts[-1].lower()


def _parse_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _derive_title(body: str) -> str:
    first_line = body.strip().splitlines()[0] if body.strip() else ""
    return first_line[:80] if first_line else "Untitled idea"


def _require_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("A valid item ID is required.") from error


def _is_visible(item: Any, *, context: ModuleViewContext) -> bool:
    if context.user_id is not None and getattr(item, "owner_user_id", None) == context.user_id:
        return True
    owner_group_id = getattr(item, "owner_group_id", None)
    if owner_group_id is not None and owner_group_id in context.group_ids:
        return True
    return context.user_id is None and not context.group_ids


def _sort_key(item: Any) -> Any:
    for key in ("captured_at", "updated_at", "created_at", "start_at", "started_on", "id"):
        value = getattr(item, key, None)
        if value is not None:
            return value
    return 0


def _serialize_object(object_type: str, item: Any) -> dict[str, Any]:
    if object_type == "idea":
        assert isinstance(item, CapturedIdea)
        return {
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "status": item.status,
            "source": item.source,
            "captured_at": item.captured_at.isoformat(),
            "tags": list(item.tags),
        }
    if object_type == "task":
        assert isinstance(item, IpeTask)
        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "priority": item.priority,
            "due_at": None if item.due_at is None else item.due_at.isoformat(),
            "tags": list(item.tags),
        }
    if object_type == "project":
        assert isinstance(item, IpeProject)
        return {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "status": item.status,
            "started_on": None if item.started_on is None else item.started_on.isoformat(),
            "target_on": None if item.target_on is None else item.target_on.isoformat(),
            "tags": list(item.tags),
            "workspace_root": item.workspace_root,
        }
    if object_type == "habit":
        assert isinstance(item, Habit)
        return {
            "id": item.id,
            "name": item.name,
            "cadence": item.cadence,
            "target_count": item.target_count,
            "streak_count": item.streak_count,
            "active": item.active,
            "tags": list(item.tags),
        }
    if object_type == "calendar_event":
        assert isinstance(item, CalendarEvent)
        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "location": item.location,
            "start_at": None if item.start_at is None else item.start_at.isoformat(),
            "end_at": None if item.end_at is None else item.end_at.isoformat(),
            "all_day": item.all_day,
            "tags": list(item.tags),
        }
    raise ValueError(f"Unsupported module object type: {object_type}")


def _get_object(service: ApmatiaIpeService, object_type: str, item_id: int) -> Any | None:
    if object_type == "idea":
        return service.ideas.get(item_id)
    if object_type == "task":
        return service.tasks.get(item_id)
    if object_type == "project":
        return service.projects.get(item_id)
    if object_type == "habit":
        return service.habits.get(item_id)
    if object_type == "calendar_event":
        return service.calendar_events.get(item_id)
    raise ValueError(f"Unsupported module object type: {object_type}")


def _delete_object(service: ApmatiaIpeService, object_type: str, item_id: int) -> bool:
    if object_type == "idea":
        return bool(service.ideas.delete(item_id))
    if object_type == "task":
        return bool(service.tasks.delete(item_id))
    if object_type == "project":
        return bool(service.projects.delete(item_id))
    if object_type == "habit":
        return bool(service.habits.delete(item_id))
    if object_type == "calendar_event":
        return bool(service.calendar_events.delete(item_id))
    raise ValueError(f"Unsupported module object type: {object_type}")
