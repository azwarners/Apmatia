import tempfile

from apmatia.modules.knowledge_wiki.manager import WikiManager
from apmatia.modules.knowledge_wiki.sqlite_repositories import SQLiteWikiManagementBundle


def test_wiki_sqlite_round_trip():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        bundle = SQLiteWikiManagementBundle(handle.name)
        manager = WikiManager(bundle.wikis, bundle.nodes)

        created = manager.create_wiki(
            "Geometry",
            owner_user_id=7,
            owner_group_id=3,
            owner_agent_id=11,
            description="Structured math notes",
        )
        branch = manager.create_branch(
            created.wiki_id,
            created.root_node_id,
            "Triangles",
            requester_user_id=7,
            requester_group_ids={3},
        )
        manager.create_leaf(
            created.wiki_id,
            branch.node_id,
            "Right triangles",
            body="Use the Pythagorean theorem.",
            requester_user_id=7,
            requester_group_ids={3},
        )

        reloaded = manager.get_wiki(created.wiki_id, requester_user_id=7, requester_group_ids={3})
        tree = manager.get_tree(created.wiki_id, requester_user_id=7, requester_group_ids={3})

        assert reloaded is not None
        assert reloaded.owner_agent_id == 11
        assert reloaded.description == "Structured math notes"
        assert tree["root"]["children"][0]["title"] == "Triangles"
        assert tree["root"]["children"][0]["children"][0]["title"] == "Right triangles"
