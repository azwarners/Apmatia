from apmatia.modules.knowledge_wiki.models import KnowledgeObject, Wiki, WikiNode


def test_knowledge_object_preserves_owner_fields():
    knowledge = KnowledgeObject(owner_user_id=7, owner_group_id=8, owner_agent_id=9, mode=0o640)

    assert knowledge.owner_user_id == 7
    assert knowledge.owner_group_id == 8
    assert knowledge.owner_agent_id == 9
    assert knowledge.mode == 0o640


def test_wiki_defaults_and_root_identifier():
    wiki = Wiki(id="wiki_demo", title="Calculus", root_node_id="wn_root")

    assert wiki.wiki_id == "wiki_demo"
    assert wiki.title == "Calculus"
    assert wiki.description is None
    assert wiki.root_node_id == "wn_root"


def test_branch_nodes_clear_body_content():
    node = WikiNode(
        id="wn_branch",
        wiki_id="wiki_demo",
        parent_id=None,
        node_type="branch",
        title="Outline",
        body="ignored",
    )

    assert node.body == ""
