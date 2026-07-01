from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core.module_view_runtime import ModuleViewContext
from src.core.registry import CommandContribution, ViewContribution
from src.core.wiki_management_runtime import get_wiki_manager


WORKSIM_ORG_CHART_MODULE_ID = "apmatia_worksim"
WORKSIM_ORG_CHART_WIKI_TITLE = "Apmatia Workplace Org Chart"
WORKSIM_ORG_CHART_ROOT_TITLE = "User"
WORKSIM_ORG_CHART_METADATA = {
    "module": WORKSIM_ORG_CHART_MODULE_ID,
    "kind": "org_chart",
    "root_label": WORKSIM_ORG_CHART_ROOT_TITLE,
}


class ApmatiaWorksimModuleViewProvider:
    def list_items(
        self,
        *,
        view: ViewContribution,
        context: ModuleViewContext,
    ) -> list[dict[str, Any]]:
        object_type = _object_type(view.metadata)
        if object_type != "org_chart_node":
            raise ValueError(f"Unsupported worksim object type: {object_type}")

        user_id = _require_user_id(context)
        wiki = _ensure_org_chart_wiki(user_id)
        manager = get_wiki_manager()
        nodes = manager.flatten_tree(
            wiki.wiki_id,
            requester_user_id=user_id,
            requester_group_ids=set(context.group_ids),
        )
        return [_serialize_node(node, wiki) for node in nodes]

    def execute_command(
        self,
        *,
        command: CommandContribution,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any] | None:
        metadata = dict(command.metadata or {})
        object_type = _object_type(metadata)
        if object_type != "org_chart_node":
            raise ValueError(f"Unsupported worksim object type: {object_type}")

        verb = str(metadata.get("verb") or "").strip().lower() or _command_verb(command.command_id)
        if verb == "list":
            return {"items": self.list_items(view=_view_from_command(command), context=context)}
        if verb == "create":
            return self._create_node(payload=payload, context=context)
        if verb == "edit":
            return self._edit_node(payload=payload, context=context)
        if verb == "delete":
            return self._delete_node(payload=payload, context=context)
        raise ValueError(f"Unsupported module command verb for now: {verb}")

    def _create_node(
        self,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        user_id = _require_user_id(context)
        wiki = _ensure_org_chart_wiki(user_id)
        manager = get_wiki_manager()

        title = _require_title(payload)
        body = str(payload.get("body") or "").strip()
        node_type = _normalize_node_type(payload.get("node_type"), default="branch")
        parent_id = _normalize_parent_id(
            payload.get("parent_id"),
            root_node_id=wiki.root_node_id,
            current_parent_id=None,
            default_to_root=True,
        )
        sort_order = _optional_int(payload.get("sort_order"))

        if node_type == "leaf":
            node = manager.create_leaf(
                wiki.wiki_id,
                parent_id,
                title,
                body=body,
                requester_user_id=user_id,
                requester_group_ids=set(context.group_ids),
                sort_order=sort_order,
            )
        else:
            node = manager.create_branch(
                wiki.wiki_id,
                parent_id,
                title,
                requester_user_id=user_id,
                requester_group_ids=set(context.group_ids),
                sort_order=sort_order,
            )
        refreshed = _require_node(manager, wiki.wiki_id, node.node_id, context)
        return {
            "status": "created",
            "item": _serialize_node(refreshed, wiki),
        }

    def _edit_node(
        self,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        user_id = _require_user_id(context)
        wiki = _ensure_org_chart_wiki(user_id)
        manager = get_wiki_manager()
        node_id = _require_node_id(payload.get("item_id"))
        current = _require_node(manager, wiki.wiki_id, node_id, context)

        if "title" in payload:
            new_title = str(payload.get("title") or "").strip()
            if not new_title:
                raise ValueError("A node title is required.")
        else:
            new_title = str(current["title"])

        if "body" in payload:
            new_body = str(payload.get("body") or "").strip()
        else:
            new_body = str(current["body"])

        new_node_type = _normalize_node_type(payload.get("node_type"), default=current["node_type"])
        new_sort_order = _optional_int(payload.get("sort_order"), default=int(current["sort_order"]))
        new_parent_id = _normalize_parent_id(
            payload.get("parent_id") if "parent_id" in payload else current["parent_id"],
            root_node_id=wiki.root_node_id,
            current_parent_id=current["parent_id"],
            default_to_root=False,
        )

        moved = False
        if new_parent_id is not None and new_parent_id != current["parent_id"]:
            manager.move_node(
                node_id,
                new_parent_id=new_parent_id,
                requester_user_id=user_id,
                requester_group_ids=set(context.group_ids),
                new_sort_order=new_sort_order,
            )
            moved = True
        elif new_sort_order != current["sort_order"]:
            manager.reorder_node(
                node_id,
                requester_user_id=user_id,
                requester_group_ids=set(context.group_ids),
                new_sort_order=new_sort_order,
            )

        updates: dict[str, Any] = {}
        if new_title != current["title"]:
            updates["title"] = new_title
        if new_body != current["body"]:
            updates["body"] = new_body
        if new_node_type != current["node_type"]:
            updates["node_type"] = new_node_type
        if not moved and new_sort_order != current["sort_order"]:
            updates["sort_order"] = new_sort_order
        if updates:
            manager.update_node(
                node_id,
                requester_user_id=user_id,
                requester_group_ids=set(context.group_ids),
                **updates,
            )

        refreshed = _require_node(manager, wiki.wiki_id, node_id, context)
        return {
            "status": "updated",
            "item": _serialize_node(refreshed, wiki),
        }

    def _delete_node(
        self,
        *,
        payload: Mapping[str, Any],
        context: ModuleViewContext,
    ) -> dict[str, Any]:
        user_id = _require_user_id(context)
        wiki = _ensure_org_chart_wiki(user_id)
        manager = get_wiki_manager()
        node_id = _require_node_id(payload.get("item_id"))
        deleted = manager.delete_node(
            node_id,
            requester_user_id=user_id,
            requester_group_ids=set(context.group_ids),
        )
        return {
            "status": "deleted" if deleted else "not_found",
            "item_id": node_id,
            "deleted": bool(deleted),
            "wiki_id": wiki.wiki_id,
        }


def _ensure_org_chart_wiki(user_id: int):
    manager = get_wiki_manager()
    for wiki in manager.list_wikis(requester_user_id=user_id, owner_user_id=user_id):
        metadata = dict(getattr(wiki, "metadata", {}) or {})
        if metadata.get("module") == WORKSIM_ORG_CHART_MODULE_ID and metadata.get("kind") == "org_chart":
            return wiki
    return manager.create_wiki(
        WORKSIM_ORG_CHART_WIKI_TITLE,
        owner_user_id=user_id,
        owner_agent_id=None,
        metadata=dict(WORKSIM_ORG_CHART_METADATA),
        root_title=WORKSIM_ORG_CHART_ROOT_TITLE,
    )


def _serialize_node(node: Mapping[str, Any], wiki: Any) -> dict[str, Any]:
    data = dict(node)
    data["owner_user_id"] = wiki.owner_user_id
    data["owner_agent_id"] = wiki.owner_agent_id
    data["is_root"] = str(node.get("id") or "") == str(wiki.root_node_id)
    data["metadata"] = dict(getattr(wiki, "metadata", {}) or {})
    return data


def _view_from_command(command: CommandContribution) -> ViewContribution:
    view_id = str(command.metadata.get("collection_view_id") or "").strip()
    return ViewContribution(
        module_id=command.module_id,
        action_id=command.action_id,
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


def _require_user_id(context: ModuleViewContext) -> int:
    if context.user_id is None:
        raise ValueError("The workplace org chart requires an authenticated user.")
    return int(context.user_id)


def _require_node(
    manager: Any,
    wiki_id: str,
    node_id: str,
    context: ModuleViewContext,
) -> dict[str, Any]:
    for node in manager.flatten_tree(
        wiki_id,
        requester_user_id=_require_user_id(context),
        requester_group_ids=set(context.group_ids),
    ):
        if str(node["id"]) == str(node_id):
            return dict(node)
    raise ValueError(f"Org chart node not found: {node_id}")


def _require_node_id(value: Any) -> str:
    node_id = str(value or "").strip()
    if not node_id:
        raise ValueError("A valid node ID is required.")
    return node_id


def _require_title(payload: Mapping[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("A node title is required.")
    return title


def _normalize_node_type(value: Any, *, default: str) -> str:
    text = str(value or "").strip().lower()
    node_type = text or default
    if node_type not in {"branch", "leaf"}:
        raise ValueError("Node type must be branch or leaf.")
    return node_type


def _normalize_parent_id(
    value: Any,
    *,
    root_node_id: str,
    current_parent_id: str | None,
    default_to_root: bool,
) -> str | None:
    text = str(value or "").strip()
    if not text:
        return root_node_id if default_to_root else current_parent_id
    if text.lower() in {"root", "user"}:
        return root_node_id
    return text


def _optional_int(value: Any, *, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Sort order must be an integer.") from error
