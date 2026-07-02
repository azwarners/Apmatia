from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from apmatia.lib.apmatia_core.models import utc_now
from apmatia.lib.apmatia_core.permissions import can_read, can_write

from .models import Wiki, WikiNode, new_wiki_id, new_wiki_node_id
from .repositories import WikiNodeRepository, WikiRepository
from .services import WikiService


class WikiManager(WikiService):
    def __init__(self, wiki_repo: WikiRepository, node_repo: WikiNodeRepository):
        self._wiki_repo = wiki_repo
        self._node_repo = node_repo

    def create_wiki(self, title: str, **kwargs) -> Wiki:
        now = utc_now()
        wiki_id = str(kwargs.get("wiki_id") or new_wiki_id())
        root_node_id = str(kwargs.get("root_node_id") or new_wiki_node_id())
        wiki = Wiki(
            id=wiki_id,
            owner_user_id=kwargs.get("owner_user_id"),
            owner_group_id=kwargs.get("owner_group_id"),
            owner_agent_id=kwargs.get("owner_agent_id"),
            mode=kwargs.get("mode", 0o000),
            created_at=now,
            updated_at=now,
            title=title,
            description=kwargs.get("description"),
            root_node_id=root_node_id,
            metadata=dict(kwargs.get("metadata", {})),
        )
        root_title = str(kwargs.get("root_title") or title).strip() or title
        root = WikiNode(
            id=root_node_id,
            wiki_id=wiki.wiki_id,
            parent_id=None,
            node_type="branch",
            title=root_title,
            body="",
            sort_order=0,
            created_at=now,
            updated_at=now,
        )
        self._wiki_repo.create(wiki)
        self._node_repo.create(root)
        return wiki

    def get_wiki(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> Wiki | None:
        wiki = self._wiki_repo.get(wiki_id)
        if wiki is None:
            return None
        if not self._can_view(wiki, requester_user_id, requester_group_ids or set()):
            return None
        return wiki

    def list_wikis(
        self,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        owner_user_id: int | None = None,
        owner_group_id: int | None = None,
        owner_agent_id: int | None = None,
    ) -> list[Wiki]:
        results: list[Wiki] = []
        for wiki in sorted(self._wiki_repo.list_all(), key=lambda item: item.updated_at, reverse=True):
            if owner_user_id is not None and wiki.owner_user_id != owner_user_id:
                continue
            if owner_group_id is not None and wiki.owner_group_id != owner_group_id:
                continue
            if owner_agent_id is not None and wiki.owner_agent_id != owner_agent_id:
                continue
            if not self._can_view(wiki, requester_user_id, requester_group_ids or set()):
                continue
            results.append(wiki)
        return results

    def update_wiki(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        **updates,
    ) -> Wiki:
        wiki = self._require_writable_wiki(wiki_id, requester_user_id, requester_group_ids or set())
        updated = replace(
            wiki,
            title=str(updates.get("title", wiki.title)),
            description=updates.get("description", wiki.description),
            owner_user_id=updates.get("owner_user_id", wiki.owner_user_id),
            owner_group_id=updates.get("owner_group_id", wiki.owner_group_id),
            owner_agent_id=updates.get("owner_agent_id", wiki.owner_agent_id),
            mode=updates.get("mode", wiki.mode),
            metadata=dict(updates.get("metadata", wiki.metadata)),
            updated_at=utc_now(),
        )
        self._wiki_repo.update(updated)
        return updated

    def delete_wiki(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> bool:
        wiki = self._require_writable_wiki(wiki_id, requester_user_id, requester_group_ids or set())
        for node in self._node_repo.list_by_wiki(wiki.wiki_id):
            self._node_repo.delete(node.node_id)
        return self._wiki_repo.delete(wiki.wiki_id)

    def create_branch(
        self,
        wiki_id: str,
        parent_id: str,
        title: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        sort_order: int | None = None,
    ) -> WikiNode:
        return self._create_node(
            wiki_id,
            parent_id,
            title,
            node_type="branch",
            body="",
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
            sort_order=sort_order,
        )

    def create_leaf(
        self,
        wiki_id: str,
        parent_id: str,
        title: str,
        *,
        body: str = "",
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        sort_order: int | None = None,
    ) -> WikiNode:
        return self._create_node(
            wiki_id,
            parent_id,
            title,
            node_type="leaf",
            body=body,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
            sort_order=sort_order,
        )

    def update_node(
        self,
        node_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        **updates,
    ) -> WikiNode:
        node = self._require_writable_node(node_id, requester_user_id, requester_group_ids or set())
        new_type = str(updates.get("node_type", node.node_type))
        title = str(updates.get("title", node.title))
        body = updates.get("body", node.body)
        updated = replace(
            node,
            node_type=new_type,
            title=title,
            body="" if new_type == "branch" else str(body or ""),
            sort_order=int(updates.get("sort_order", node.sort_order)),
            updated_at=utc_now(),
        )
        self._node_repo.update(updated)
        if updated.parent_id is not None:
            self._normalize_sibling_order(updated.wiki_id, updated.parent_id)
        self._touch_wiki(updated.wiki_id)
        return self._node_repo.get(updated.node_id) or updated

    def move_node(
        self,
        node_id: str,
        *,
        new_parent_id: str,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        new_sort_order: int | None = None,
    ) -> WikiNode:
        node = self._require_writable_node(node_id, requester_user_id, requester_group_ids or set())
        wiki = self._require_writable_wiki(node.wiki_id, requester_user_id, requester_group_ids or set())
        if node.node_id == wiki.root_node_id:
            raise ValueError("Root wiki node cannot be moved.")
        new_parent = self._node_repo.get(str(new_parent_id))
        if new_parent is None or new_parent.wiki_id != node.wiki_id:
            raise ValueError("Parent wiki node not found.")
        if new_parent.node_type != "branch":
            raise ValueError("Parent wiki node must be a branch.")
        subtree_ids = set(self._collect_subtree_ids(node.wiki_id, node.node_id))
        if new_parent.node_id in subtree_ids:
            raise ValueError("Wiki node cannot be moved into itself or its descendants.")

        old_parent_id = node.parent_id
        siblings = self._sorted_children(node.wiki_id, new_parent.node_id)
        target_index = len(siblings) if new_sort_order is None else max(0, min(int(new_sort_order), len(siblings)))
        moved = replace(node, parent_id=new_parent.node_id, sort_order=target_index, updated_at=utc_now())
        self._node_repo.update(moved)
        if old_parent_id is not None:
            self._normalize_sibling_order(node.wiki_id, old_parent_id)
        self._normalize_sibling_order(node.wiki_id, new_parent.node_id)
        self._touch_wiki(node.wiki_id)
        return self._node_repo.get(node.node_id) or moved

    def reorder_node(
        self,
        node_id: str,
        *,
        new_sort_order: int,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> WikiNode:
        node = self._require_writable_node(node_id, requester_user_id, requester_group_ids or set())
        if node.parent_id is None:
            raise ValueError("Root wiki node cannot be reordered.")
        siblings = [child for child in self._sorted_children(node.wiki_id, node.parent_id) if child.node_id != node.node_id]
        index = max(0, min(int(new_sort_order), len(siblings)))
        siblings.insert(index, replace(node, updated_at=utc_now()))
        self._persist_ordered_children(siblings)
        self._touch_wiki(node.wiki_id)
        return self._node_repo.get(node.node_id) or node

    def delete_node(
        self,
        node_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> bool:
        node = self._require_writable_node(node_id, requester_user_id, requester_group_ids or set())
        wiki = self._require_writable_wiki(node.wiki_id, requester_user_id, requester_group_ids or set())
        if node.node_id == wiki.root_node_id:
            raise ValueError("Root wiki node cannot be deleted.")
        parent_id = node.parent_id
        for subtree_node_id in reversed(self._collect_subtree_ids(node.wiki_id, node.node_id)):
            self._node_repo.delete(subtree_node_id)
        if parent_id is not None:
            self._normalize_sibling_order(node.wiki_id, parent_id)
        self._touch_wiki(node.wiki_id)
        return True

    def get_tree(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> dict:
        wiki = self.get_wiki(wiki_id, requester_user_id=requester_user_id, requester_group_ids=requester_group_ids or set())
        if wiki is None:
            raise ValueError(f"Wiki not found: {wiki_id}")
        nodes = self._node_repo.list_by_wiki(wiki.wiki_id)
        by_parent: dict[str | None, list[WikiNode]] = defaultdict(list)
        for node in nodes:
            by_parent[node.parent_id].append(node)
        for siblings in by_parent.values():
            siblings.sort(key=lambda item: (item.sort_order, item.created_at))
        root = self._node_repo.get(wiki.root_node_id)
        if root is None:
            raise ValueError(f"Wiki root node is missing: {wiki.wiki_id}")
        return {
            "wiki": self._wiki_to_dict(wiki),
            "root": self._build_tree_node(root, by_parent),
        }

    def flatten_tree(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> list[dict]:
        tree = self.get_tree(
            wiki_id,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
        )
        flattened: list[dict] = []

        def _walk(node: dict, depth: int, path: list[str]) -> None:
            current_path = [*path, str(node["title"])]
            flattened.append(
                {
                    "id": node["id"],
                    "wiki_id": node["wiki_id"],
                    "parent_id": node["parent_id"],
                    "node_type": node["node_type"],
                    "title": node["title"],
                    "body": node["body"],
                    "sort_order": node["sort_order"],
                    "depth": depth,
                    "path": " / ".join(current_path),
                }
            )
            for child in node.get("children", []):
                _walk(child, depth + 1, current_path)

        _walk(tree["root"], 0, [])
        return flattened

    def search_wiki(
        self,
        wiki_id: str,
        query: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
        limit: int | None = 20,
    ) -> list[dict]:
        text = str(query or "").strip().lower()
        if not text:
            return []
        results: list[dict] = []
        for item in self.flatten_tree(
            wiki_id,
            requester_user_id=requester_user_id,
            requester_group_ids=requester_group_ids or set(),
        ):
            haystack = f"{item['title']} {item['body']} {item['path']}".lower()
            if text not in haystack:
                continue
            results.append(item)
            if limit is not None and len(results) >= int(limit):
                break
        return results

    def _create_node(
        self,
        wiki_id: str,
        parent_id: str,
        title: str,
        *,
        node_type: str,
        body: str,
        requester_user_id: int | None,
        requester_group_ids: set[int],
        sort_order: int | None,
    ) -> WikiNode:
        self._require_writable_wiki(wiki_id, requester_user_id, requester_group_ids)
        parent = self._node_repo.get(str(parent_id))
        if parent is None or parent.wiki_id != wiki_id:
            raise ValueError("Parent wiki node not found.")
        if parent.node_type != "branch":
            raise ValueError("Parent wiki node must be a branch.")
        siblings = self._sorted_children(wiki_id, parent.node_id)
        next_sort_order = len(siblings) if sort_order is None else max(0, min(int(sort_order), len(siblings)))
        now = utc_now()
        node = WikiNode(
            id=new_wiki_node_id(),
            wiki_id=wiki_id,
            parent_id=parent.node_id,
            node_type=node_type,
            title=title,
            body=body,
            sort_order=next_sort_order,
            created_at=now,
            updated_at=now,
        )
        self._node_repo.create(node)
        self._normalize_sibling_order(wiki_id, parent.node_id)
        self._touch_wiki(wiki_id)
        return self._node_repo.get(node.node_id) or node

    def _can_view(self, wiki: Wiki, requester_user_id: int | None, requester_group_ids: set[int]) -> bool:
        if requester_user_id is None:
            return False
        if wiki.owner_user_id is not None and wiki.owner_user_id == requester_user_id:
            return True
        return can_read(wiki, requester_user_id, requester_group_ids)

    def _require_writable_wiki(self, wiki_id: str, requester_user_id: int | None, requester_group_ids: set[int]) -> Wiki:
        wiki = self._wiki_repo.get(wiki_id)
        if wiki is None:
            raise ValueError(f"Wiki not found: {wiki_id}")
        if requester_user_id is None or not can_write(wiki, requester_user_id, requester_group_ids):
            if wiki.owner_user_id != requester_user_id:
                raise PermissionError("Wiki is not writable by this user.")
        return wiki

    def _require_writable_node(self, node_id: str, requester_user_id: int | None, requester_group_ids: set[int]) -> WikiNode:
        node = self._node_repo.get(node_id)
        if node is None:
            raise ValueError(f"Wiki node not found: {node_id}")
        self._require_writable_wiki(node.wiki_id, requester_user_id, requester_group_ids)
        return node

    def _touch_wiki(self, wiki_id: str) -> None:
        wiki = self._wiki_repo.get(wiki_id)
        if wiki is None:
            return
        self._wiki_repo.update(replace(wiki, updated_at=utc_now()))

    def _sorted_children(self, wiki_id: str, parent_id: str) -> list[WikiNode]:
        return sorted(
            [node for node in self._node_repo.list_by_wiki(wiki_id) if node.parent_id == parent_id],
            key=lambda item: (item.sort_order, item.created_at),
        )

    def _normalize_sibling_order(self, wiki_id: str, parent_id: str) -> None:
        self._persist_ordered_children(self._sorted_children(wiki_id, parent_id))

    def _persist_ordered_children(self, siblings: list[WikiNode]) -> None:
        now = utc_now()
        for index, sibling in enumerate(siblings):
            if sibling.sort_order == index and sibling.updated_at == now:
                continue
            self._node_repo.update(replace(sibling, sort_order=index, updated_at=now))

    def _collect_subtree_ids(self, wiki_id: str, root_node_id: str) -> list[str]:
        nodes = self._node_repo.list_by_wiki(wiki_id)
        by_parent: dict[str | None, list[WikiNode]] = defaultdict(list)
        for node in nodes:
            by_parent[node.parent_id].append(node)
        collected: list[str] = []
        stack = [root_node_id]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            collected.append(current)
            for child in by_parent.get(current, []):
                stack.append(child.node_id)
        return collected

    def _build_tree_node(self, node: WikiNode, by_parent: dict[str | None, list[WikiNode]]) -> dict:
        return {
            "id": node.node_id,
            "wiki_id": node.wiki_id,
            "parent_id": node.parent_id,
            "node_type": node.node_type,
            "title": node.title,
            "body": node.body,
            "sort_order": node.sort_order,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
            "children": [
                self._build_tree_node(child, by_parent)
                for child in by_parent.get(node.node_id, [])
            ],
        }

    @staticmethod
    def _wiki_to_dict(wiki: Wiki) -> dict:
        return {
            "id": wiki.wiki_id,
            "owner_user_id": wiki.owner_user_id,
            "owner_group_id": wiki.owner_group_id,
            "owner_agent_id": wiki.owner_agent_id,
            "mode": wiki.mode,
            "title": wiki.title,
            "description": wiki.description,
            "root_node_id": wiki.root_node_id,
            "metadata": dict(wiki.metadata),
            "created_at": wiki.created_at.isoformat(),
            "updated_at": wiki.updated_at.isoformat(),
        }

