from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apmatia.lib.agent_management.services import AgentService

from .services import WikiService


@dataclass(slots=True)
class WikiTooling:
    wiki_service: WikiService

    def wiki_create_leaf(self, wiki_id: str, parent_id: str, title: str, body: str = "", **kwargs: Any) -> dict[str, Any]:
        node = self.wiki_service.create_leaf(wiki_id, parent_id, title, body=body, **kwargs)
        return _node_summary(node)

    def wiki_update_node(self, node_id: str, **updates: Any) -> dict[str, Any]:
        node = self.wiki_service.update_node(node_id, **updates)
        return _node_summary(node)

    def wiki_create_branch(self, wiki_id: str, parent_id: str, title: str, **kwargs: Any) -> dict[str, Any]:
        node = self.wiki_service.create_branch(wiki_id, parent_id, title, **kwargs)
        return _node_summary(node)

    def wiki_get_tree(self, wiki_id: str, **kwargs: Any) -> dict[str, Any]:
        return self.wiki_service.get_tree(wiki_id, **kwargs)

    def wiki_search(self, wiki_id: str, query: str, **kwargs: Any) -> dict[str, Any]:
        results = self.wiki_service.search_wiki(wiki_id, query, **kwargs)
        return {"count": len(results), "results": results}

    def wiki_move_node(self, node_id: str, new_parent_id: str, **kwargs: Any) -> dict[str, Any]:
        node = self.wiki_service.move_node(node_id, new_parent_id=new_parent_id, **kwargs)
        return _node_summary(node)

    def wiki_reorder_node(self, node_id: str, new_sort_order: int, **kwargs: Any) -> dict[str, Any]:
        node = self.wiki_service.reorder_node(node_id, new_sort_order=new_sort_order, **kwargs)
        return _node_summary(node)


def _node_summary(node: Any) -> dict[str, Any]:
    return {
        "id": node.id,
        "wiki_id": node.wiki_id,
        "parent_id": node.parent_id,
        "node_type": node.node_type,
        "title": node.title,
        "body": node.body,
        "sort_order": node.sort_order,
        "created_at": node.created_at.isoformat(),
        "updated_at": node.updated_at.isoformat(),
    }


def wiki_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "wiki_create_branch",
            "description": (
                "Create a branch in the focused wiki tree. "
                "Use branches to shape the outline, group ideas, and hang child branches or leaves beneath them."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": "string"},
                    "title": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["parent_id", "title"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": ["string", "null"]},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["id", "wiki_id", "node_type", "title", "sort_order"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_create_branch",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_create_leaf",
            "description": (
                "Create a leaf in the focused wiki tree. "
                "Use leaves for concrete notes, explanations, examples, or other terminal knowledge nodes."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["parent_id", "title"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": ["string", "null"]},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["id", "wiki_id", "node_type", "title", "sort_order"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_create_leaf",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_update_node",
            "description": (
                "Rename or update any wiki node in the focused tree. "
                "Use this to refine branch titles, leaf titles, or leaf bodies without changing the node's place in the tree."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["node_id"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": ["string", "null"]},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["id", "wiki_id", "node_type", "title", "sort_order"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_update_node",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_get_tree",
            "description": (
                "Retrieve the focused wiki tree visible to the calling agent. "
                "This returns the root branch and every nested child so the agent can browse or plan changes against the live structure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "wiki_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "wiki": {"type": "object"},
                    "root": {"type": "object"},
                },
                "required": ["wiki", "root"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_get_tree",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_search",
            "description": (
                "Search the focused wiki content visible to the calling agent. "
                "Use search to find existing branches or leaves before creating duplicates."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "wiki_id": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "results": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["count", "results"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_search",
            "enabled": True,
            "confirmation_required": False,
            "read_only": True,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_move_node",
            "description": (
                "Move a wiki node into another branch in the focused tree. "
                "Use this to reshape the tree, group related ideas, or correct branch placement."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "new_parent_id": {"type": "string"},
                    "new_sort_order": {"type": "integer"},
                },
                "required": ["node_id", "new_parent_id"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": ["string", "null"]},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["id", "wiki_id", "node_type", "title", "sort_order"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_move_node",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
        {
            "name": "wiki_reorder_node",
            "description": (
                "Change the order of a wiki node among its siblings in the focused tree. "
                "Use this to polish the tree layout after branches and leaves are in the right place."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "new_sort_order": {"type": "integer"},
                },
                "required": ["node_id", "new_sort_order"],
                "additionalProperties": False,
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "wiki_id": {"type": "string"},
                    "parent_id": {"type": ["string", "null"]},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "sort_order": {"type": "integer"},
                },
                "required": ["id", "wiki_id", "node_type", "title", "sort_order"],
                "additionalProperties": True,
            },
            "provider_id": "builtin.wiki_reorder_node",
            "enabled": True,
            "confirmation_required": False,
            "read_only": False,
            "metadata": {"builtin": True},
        },
    ]


@dataclass(slots=True)
class WikiToolProvider:
    provider_id: str
    action: str
    wiki_service: WikiService
    agent_service: AgentService

    def execute(self, arguments: dict[str, Any], *, tool_call: Any = None) -> Any:
        if tool_call is None:
            raise ValueError("Tool call context is required.")
        agent = self.agent_service.get_agent(int(tool_call.requester_agent_id))
        if agent is None or agent.id is None:
            raise ValueError(f"Calling agent is unavailable: {tool_call.requester_agent_id}")
        if agent.owner_user_id is None:
            agent = self._restore_agent_owner(agent, tool_call)
        if agent.owner_user_id is None:
            raise ValueError(
                f"Calling agent {agent.id} has no owner_user_id. "
                "Re-save the agent while authenticated, or use it from a discussion owned by a user once so Apmatia can repair it."
            )
        requester_group_ids = {agent.owner_group_id} if agent.owner_group_id is not None else set()

        if self.action in {"create_branch", "create_leaf", "get_tree", "search"}:
            wiki_id = self._resolve_wiki_id(arguments, tool_call)
        else:
            wiki_id = None

        if self.action == "create_branch":
            node = self.wiki_service.create_branch(
                str(wiki_id),
                parent_id=str(arguments["parent_id"]),
                title=str(arguments["title"]),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                sort_order=arguments.get("sort_order"),
            )
            return _node_summary(node)

        if self.action == "create_leaf":
            node = self.wiki_service.create_leaf(
                str(wiki_id),
                parent_id=str(arguments["parent_id"]),
                title=str(arguments["title"]),
                body=str(arguments.get("body", "")),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                sort_order=arguments.get("sort_order"),
            )
            return _node_summary(node)

        if self.action == "update_node":
            updates: dict[str, Any] = {}
            if "title" in arguments:
                updates["title"] = arguments["title"]
            if "body" in arguments:
                updates["body"] = arguments["body"]
            node = self.wiki_service.update_node(
                str(arguments["node_id"]),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                **updates,
            )
            return _node_summary(node)

        if self.action == "get_tree":
            return self.wiki_service.get_tree(
                str(wiki_id),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
            )

        if self.action == "search":
            results = self.wiki_service.search_wiki(
                str(wiki_id),
                str(arguments["query"]),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                limit=int(arguments["limit"]) if arguments.get("limit") is not None else 20,
            )
            return {"count": len(results), "results": results}

        if self.action == "move_node":
            node = self.wiki_service.move_node(
                str(arguments["node_id"]),
                new_parent_id=str(arguments["new_parent_id"]),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                new_sort_order=arguments.get("new_sort_order"),
            )
            return _node_summary(node)

        if self.action == "reorder_node":
            node = self.wiki_service.reorder_node(
                str(arguments["node_id"]),
                requester_user_id=agent.owner_user_id,
                requester_group_ids=requester_group_ids,
                new_sort_order=int(arguments["new_sort_order"]),
            )
            return _node_summary(node)

        raise ValueError(f"Unsupported wiki action: {self.action}")

    def _resolve_wiki_id(self, arguments: dict[str, Any], tool_call: Any) -> str:
        if arguments.get("wiki_id"):
            return str(arguments["wiki_id"])
        discussion_id = getattr(tool_call, "discussion_id", None)
        if not discussion_id:
            raise ValueError("wiki_id is required when no focused tutor wiki is attached to the discussion.")
        from apmatia.lib.discussions import discussion_state

        discussion = discussion_state._get_discussion(str(discussion_id))
        focused_wiki_id = None if discussion is None else getattr(discussion, "focused_wiki_id", None)
        if focused_wiki_id is None or not str(focused_wiki_id).strip():
            raise ValueError("The current discussion does not have a focused wiki.")
        return str(focused_wiki_id)

    def _restore_agent_owner(self, agent: Any, tool_call: Any) -> Any:
        discussion_id = getattr(tool_call, "discussion_id", None)
        if not discussion_id:
            return agent
        from apmatia.lib.discussions import discussion_state

        discussion = discussion_state._get_discussion(str(discussion_id))
        if discussion is None or discussion.owner_user_id is None:
            return agent
        try:
            repaired = self.agent_service.update_agent(
                int(agent.id),
                owner_user_id=discussion.owner_user_id,
            )
        except Exception:
            return agent
        return repaired


def build_wiki_tool_providers(
    wiki_service: WikiService,
    agent_service: AgentService,
) -> list[WikiToolProvider]:
    return [
        WikiToolProvider("builtin.wiki_create_branch", "create_branch", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_create_leaf", "create_leaf", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_update_node", "update_node", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_get_tree", "get_tree", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_search", "search", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_move_node", "move_node", wiki_service, agent_service),
        WikiToolProvider("builtin.wiki_reorder_node", "reorder_node", wiki_service, agent_service),
    ]
