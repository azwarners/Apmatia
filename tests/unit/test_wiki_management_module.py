from __future__ import annotations

from dataclasses import replace

import pytest

from apmatia.modules.knowledge_wiki.manager import WikiManager
from apmatia.modules.knowledge_wiki.models import Wiki, WikiNode
from apmatia.modules.knowledge_wiki.repositories import WikiNodeRepository, WikiRepository


class InMemoryWikiRepository(WikiRepository):
    def __init__(self) -> None:
        self._wikis: dict[str, Wiki] = {}

    def create(self, wiki: Wiki) -> str:
        self._wikis[wiki.wiki_id] = wiki
        return wiki.wiki_id

    def get(self, wiki_id: str) -> Wiki | None:
        return self._wikis.get(wiki_id)

    def list_all(self) -> list[Wiki]:
        return list(self._wikis.values())

    def update(self, wiki: Wiki) -> None:
        self._wikis[wiki.wiki_id] = wiki

    def delete(self, wiki_id: str) -> bool:
        return self._wikis.pop(wiki_id, None) is not None


class InMemoryWikiNodeRepository(WikiNodeRepository):
    def __init__(self) -> None:
        self._nodes: dict[str, WikiNode] = {}

    def create(self, node: WikiNode) -> str:
        self._nodes[node.node_id] = node
        return node.node_id

    def get(self, node_id: str) -> WikiNode | None:
        return self._nodes.get(node_id)

    def list_by_wiki(self, wiki_id: str) -> list[WikiNode]:
        return [node for node in self._nodes.values() if node.wiki_id == wiki_id]

    def update(self, node: WikiNode) -> None:
        self._nodes[node.node_id] = node

    def delete(self, node_id: str) -> bool:
        return self._nodes.pop(node_id, None) is not None


@pytest.fixture
def wiki_manager() -> WikiManager:
    return WikiManager(InMemoryWikiRepository(), InMemoryWikiNodeRepository())


def test_create_wiki_starts_with_root_branch(wiki_manager: WikiManager):
    created = wiki_manager.create_wiki("Algebra I", owner_user_id=7, owner_agent_id=11)
    tree = wiki_manager.get_tree(created.wiki_id, requester_user_id=7, requester_group_ids=set())

    assert created.owner_agent_id == 11
    assert tree["wiki"]["root_node_id"] == tree["root"]["id"]
    assert tree["root"]["node_type"] == "branch"
    assert tree["root"]["title"] == "Algebra I"


def test_nested_branches_and_leaves_are_retrievable(wiki_manager: WikiManager):
    wiki = wiki_manager.create_wiki("Physics", owner_user_id=7)
    root_id = wiki.root_node_id
    branch = wiki_manager.create_branch(wiki.wiki_id, root_id, "Kinematics", requester_user_id=7, requester_group_ids=set())
    leaf = wiki_manager.create_leaf(
        wiki.wiki_id,
        branch.node_id,
        "Velocity",
        body="Rate of change of position.",
        requester_user_id=7,
        requester_group_ids=set(),
    )

    tree = wiki_manager.get_tree(wiki.wiki_id, requester_user_id=7, requester_group_ids=set())
    flattened = wiki_manager.flatten_tree(wiki.wiki_id, requester_user_id=7, requester_group_ids=set())

    assert tree["root"]["children"][0]["title"] == "Kinematics"
    assert tree["root"]["children"][0]["children"][0]["title"] == "Velocity"
    assert leaf.node_id in {item["id"] for item in flattened}


def test_move_and_reorder_nodes(wiki_manager: WikiManager):
    wiki = wiki_manager.create_wiki("Chemistry", owner_user_id=7)
    root_id = wiki.root_node_id
    branch_a = wiki_manager.create_branch(wiki.wiki_id, root_id, "Atoms", requester_user_id=7, requester_group_ids=set())
    branch_b = wiki_manager.create_branch(wiki.wiki_id, root_id, "Molecules", requester_user_id=7, requester_group_ids=set())
    leaf = wiki_manager.create_leaf(
        wiki.wiki_id,
        branch_a.node_id,
        "Electron",
        body="Negatively charged particle.",
        requester_user_id=7,
        requester_group_ids=set(),
    )

    moved = wiki_manager.move_node(
        leaf.node_id,
        new_parent_id=branch_b.node_id,
        requester_user_id=7,
        requester_group_ids=set(),
    )
    reordered = wiki_manager.reorder_node(
        branch_b.node_id,
        new_sort_order=0,
        requester_user_id=7,
        requester_group_ids=set(),
    )
    tree = wiki_manager.get_tree(wiki.wiki_id, requester_user_id=7, requester_group_ids=set())

    assert moved.parent_id == branch_b.node_id
    assert reordered.sort_order == 0
    assert tree["root"]["children"][0]["title"] == "Molecules"
    assert tree["root"]["children"][0]["children"][0]["title"] == "Electron"


def test_delete_subtree_removes_descendants(wiki_manager: WikiManager):
    wiki = wiki_manager.create_wiki("Biology", owner_user_id=7)
    branch = wiki_manager.create_branch(wiki.wiki_id, wiki.root_node_id, "Cells", requester_user_id=7, requester_group_ids=set())
    wiki_manager.create_leaf(
        wiki.wiki_id,
        branch.node_id,
        "Mitochondria",
        body="Powerhouse.",
        requester_user_id=7,
        requester_group_ids=set(),
    )

    wiki_manager.delete_node(branch.node_id, requester_user_id=7, requester_group_ids=set())
    tree = wiki_manager.get_tree(wiki.wiki_id, requester_user_id=7, requester_group_ids=set())

    assert tree["root"]["children"] == []


def test_search_returns_matching_paths(wiki_manager: WikiManager):
    wiki = wiki_manager.create_wiki("Spanish", owner_user_id=7)
    wiki_manager.create_leaf(
        wiki.wiki_id,
        wiki.root_node_id,
        "Saludos",
        body="Hola means hello.",
        requester_user_id=7,
        requester_group_ids=set(),
    )

    results = wiki_manager.search_wiki(wiki.wiki_id, "hola", requester_user_id=7, requester_group_ids=set())

    assert len(results) == 1
    assert results[0]["path"].endswith("Saludos")


def test_other_users_cannot_modify_private_wikis(wiki_manager: WikiManager):
    wiki = wiki_manager.create_wiki("Private", owner_user_id=7)

    with pytest.raises(PermissionError):
        wiki_manager.update_wiki(wiki.wiki_id, requester_user_id=8, requester_group_ids=set(), title="Nope")
