"""Knowledge wiki repository contracts."""

from __future__ import annotations

from typing import Protocol

from .models import Wiki, WikiNode


class WikiRepository(Protocol):
    def create(self, wiki: Wiki) -> str:
        raise NotImplementedError

    def get(self, wiki_id: str) -> Wiki | None:
        raise NotImplementedError

    def list_all(self) -> list[Wiki]:
        raise NotImplementedError

    def update(self, wiki: Wiki) -> None:
        raise NotImplementedError

    def delete(self, wiki_id: str) -> bool:
        raise NotImplementedError


class WikiNodeRepository(Protocol):
    def create(self, node: WikiNode) -> str:
        raise NotImplementedError

    def get(self, node_id: str) -> WikiNode | None:
        raise NotImplementedError

    def list_by_wiki(self, wiki_id: str) -> list[WikiNode]:
        raise NotImplementedError

    def update(self, node: WikiNode) -> None:
        raise NotImplementedError

    def delete(self, node_id: str) -> bool:
        raise NotImplementedError
