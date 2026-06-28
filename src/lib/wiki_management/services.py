from __future__ import annotations

from typing import Protocol

from .models import Wiki, WikiNode


class WikiService(Protocol):
    def create_wiki(self, title: str, **kwargs) -> Wiki:
        raise NotImplementedError

    def get_wiki(
        self,
        wiki_id: str,
        *,
        requester_user_id: int | None = None,
        requester_group_ids: set[int] | None = None,
    ) -> Wiki | None:
        raise NotImplementedError

    def list_wikis(self, **kwargs) -> list[Wiki]:
        raise NotImplementedError

    def update_wiki(self, wiki_id: str, **updates) -> Wiki:
        raise NotImplementedError

    def delete_wiki(self, wiki_id: str, **kwargs) -> bool:
        raise NotImplementedError

    def create_branch(self, wiki_id: str, parent_id: str, title: str, **kwargs) -> WikiNode:
        raise NotImplementedError

    def create_leaf(self, wiki_id: str, parent_id: str, title: str, **kwargs) -> WikiNode:
        raise NotImplementedError

    def update_node(self, node_id: str, **updates) -> WikiNode:
        raise NotImplementedError

    def move_node(self, node_id: str, *, new_parent_id: str, **kwargs) -> WikiNode:
        raise NotImplementedError

    def reorder_node(self, node_id: str, *, new_sort_order: int, **kwargs) -> WikiNode:
        raise NotImplementedError

    def delete_node(self, node_id: str, **kwargs) -> bool:
        raise NotImplementedError

    def get_tree(self, wiki_id: str, **kwargs) -> dict:
        raise NotImplementedError

    def flatten_tree(self, wiki_id: str, **kwargs) -> list[dict]:
        raise NotImplementedError

    def search_wiki(self, wiki_id: str, query: str, **kwargs) -> list[dict]:
        raise NotImplementedError

