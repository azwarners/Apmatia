"""SQLite persistence for the knowledge wiki module."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from apmatia.modules.persistence import SQLiteStore

from apmatia.lib.apmatia_core.models import utc_now

from .models import Wiki, WikiNode
from .repositories import WikiNodeRepository, WikiRepository


@dataclass(frozen=True, slots=True)
class WikiManagementTables:
    wikis: str = "wiki_management_wikis"
    nodes: str = "wiki_management_nodes"


class SQLiteWikiRepository(WikiRepository):
    def __init__(self, store: SQLiteStore, tables: WikiManagementTables):
        self._store = store
        self._tables = tables

    def create(self, wiki: Wiki) -> str:
        payload = {
            "wiki_id": wiki.wiki_id,
            "owner_user_id": wiki.owner_user_id,
            "owner_group_id": wiki.owner_group_id,
            "owner_agent_id": wiki.owner_agent_id,
            "mode": wiki.mode,
            "created_at": wiki.created_at.isoformat(),
            "updated_at": wiki.updated_at.isoformat(),
            "title": wiki.title,
            "description": wiki.description,
            "root_node_id": wiki.root_node_id,
            "metadata": _serialize_json(wiki.metadata),
        }
        self._store.insert(self._tables.wikis, payload)
        return wiki.wiki_id

    def get(self, wiki_id: str) -> Wiki | None:
        row = self._store.get(self._tables.wikis, wiki_id=wiki_id)
        if row is None:
            return None
        return self._row_to_wiki(row)

    def list_all(self) -> list[Wiki]:
        return [self._row_to_wiki(row) for row in self._store.find(self._tables.wikis)]

    def update(self, wiki: Wiki) -> None:
        row = self._store.get(self._tables.wikis, wiki_id=wiki.wiki_id)
        if row is None:
            raise ValueError(f"Wiki not found: {wiki.wiki_id}")
        self._store.update(
            self._tables.wikis,
            {"id": row["id"]},
            {
                "wiki_id": wiki.wiki_id,
                "owner_user_id": wiki.owner_user_id,
                "owner_group_id": wiki.owner_group_id,
                "owner_agent_id": wiki.owner_agent_id,
                "mode": wiki.mode,
                "created_at": wiki.created_at.isoformat(),
                "updated_at": wiki.updated_at.isoformat(),
                "title": wiki.title,
                "description": wiki.description,
                "root_node_id": wiki.root_node_id,
                "metadata": _serialize_json(wiki.metadata),
            },
        )

    def delete(self, wiki_id: str) -> bool:
        return self._store.delete(self._tables.wikis, wiki_id=wiki_id) > 0

    @staticmethod
    def _row_to_wiki(row: dict[str, Any]) -> Wiki:
        return Wiki(
            id=str(row.get("wiki_id") or ""),
            owner_user_id=_parse_int(row.get("owner_user_id")),
            owner_group_id=_parse_int(row.get("owner_group_id")),
            owner_agent_id=_parse_int(row.get("owner_agent_id")),
            mode=_parse_int(row.get("mode")) or 0,
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
            title=str(row.get("title", "")),
            description=row.get("description"),
            root_node_id=str(row.get("root_node_id", "")),
            metadata=_parse_json_object(row.get("metadata", "{}")),
        )


class SQLiteWikiNodeRepository(WikiNodeRepository):
    def __init__(self, store: SQLiteStore, tables: WikiManagementTables):
        self._store = store
        self._tables = tables

    def create(self, node: WikiNode) -> str:
        payload = {
            "node_id": node.node_id,
            "wiki_id": node.wiki_id,
            "parent_id": node.parent_id,
            "node_type": node.node_type,
            "title": node.title,
            "body": node.body,
            "sort_order": node.sort_order,
            "created_at": _parse_datetime(node.created_at).isoformat(),
            "updated_at": _parse_datetime(node.updated_at).isoformat(),
        }
        self._store.insert(self._tables.nodes, payload)
        return node.node_id

    def get(self, node_id: str) -> WikiNode | None:
        row = self._store.get(self._tables.nodes, node_id=node_id)
        if row is None:
            return None
        return self._row_to_node(row)

    def list_by_wiki(self, wiki_id: str) -> list[WikiNode]:
        return [
            self._row_to_node(row)
            for row in self._store.find(self._tables.nodes, wiki_id=wiki_id)
        ]

    def update(self, node: WikiNode) -> None:
        row = self._store.get(self._tables.nodes, node_id=node.node_id)
        if row is None:
            raise ValueError(f"Wiki node not found: {node.node_id}")
        self._store.update(
            self._tables.nodes,
            {"id": row["id"]},
            {
                "node_id": node.node_id,
                "wiki_id": node.wiki_id,
                "parent_id": node.parent_id,
                "node_type": node.node_type,
                "title": node.title,
                "body": node.body,
                "sort_order": node.sort_order,
                "created_at": _parse_datetime(node.created_at).isoformat(),
                "updated_at": _parse_datetime(node.updated_at).isoformat(),
            },
        )

    def delete(self, node_id: str) -> bool:
        return self._store.delete(self._tables.nodes, node_id=node_id) > 0

    @staticmethod
    def _row_to_node(row: dict[str, Any]) -> WikiNode:
        return WikiNode(
            id=str(row.get("node_id") or ""),
            wiki_id=str(row.get("wiki_id") or ""),
            parent_id=row.get("parent_id"),
            node_type=str(row.get("node_type", "leaf")),
            title=str(row.get("title", "")),
            body=str(row.get("body", "")),
            sort_order=_parse_int(row.get("sort_order")) or 0,
            created_at=_parse_datetime(row.get("created_at")),
            updated_at=_parse_datetime(row.get("updated_at")),
        )


class SQLiteWikiManagementBundle:
    def __init__(self, store: SQLiteStore | str, tables: WikiManagementTables | None = None):
        self.tables = tables or WikiManagementTables()
        self.store = SQLiteStore(store) if not isinstance(store, SQLiteStore) else store
        self.wikis = SQLiteWikiRepository(self.store, self.tables)
        self.nodes = SQLiteWikiNodeRepository(self.store, self.tables)


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_json_object(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not value:
        return utc_now()
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
