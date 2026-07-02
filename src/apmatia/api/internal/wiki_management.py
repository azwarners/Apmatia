from __future__ import annotations

from apmatia.core.wiki_management_runtime import get_wiki_manager


def create_wiki(title: str, **kwargs) -> dict:
    return _wiki_to_dict(get_wiki_manager().create_wiki(title, **kwargs))


def get_wiki(wiki_id: str, **kwargs) -> dict | None:
    wiki = get_wiki_manager().get_wiki(wiki_id, **kwargs)
    if wiki is None:
        return None
    return _wiki_to_dict(wiki)


def list_wikis(**kwargs) -> list[dict]:
    return [_wiki_to_dict(wiki) for wiki in get_wiki_manager().list_wikis(**kwargs)]


def update_wiki(wiki_id: str, **updates) -> dict:
    return _wiki_to_dict(get_wiki_manager().update_wiki(wiki_id, **updates))


def delete_wiki(wiki_id: str, **kwargs) -> bool:
    return get_wiki_manager().delete_wiki(wiki_id, **kwargs)


def create_branch(wiki_id: str, parent_id: str, title: str, **kwargs) -> dict:
    return _node_to_dict(get_wiki_manager().create_branch(wiki_id, parent_id, title, **kwargs))


def create_leaf(wiki_id: str, parent_id: str, title: str, **kwargs) -> dict:
    return _node_to_dict(get_wiki_manager().create_leaf(wiki_id, parent_id, title, **kwargs))


def update_node(node_id: str, **updates) -> dict:
    return _node_to_dict(get_wiki_manager().update_node(node_id, **updates))


def move_node(node_id: str, *, new_parent_id: str, **kwargs) -> dict:
    return _node_to_dict(get_wiki_manager().move_node(node_id, new_parent_id=new_parent_id, **kwargs))


def reorder_node(node_id: str, *, new_sort_order: int, **kwargs) -> dict:
    return _node_to_dict(get_wiki_manager().reorder_node(node_id, new_sort_order=new_sort_order, **kwargs))


def delete_node(node_id: str, **kwargs) -> bool:
    return get_wiki_manager().delete_node(node_id, **kwargs)


def get_tree(wiki_id: str, **kwargs) -> dict:
    return get_wiki_manager().get_tree(wiki_id, **kwargs)


def flatten_tree(wiki_id: str, **kwargs) -> list[dict]:
    return get_wiki_manager().flatten_tree(wiki_id, **kwargs)


def search_wiki(wiki_id: str, query: str, **kwargs) -> list[dict]:
    return get_wiki_manager().search_wiki(wiki_id, query, **kwargs)


def _wiki_to_dict(wiki) -> dict:
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


def _node_to_dict(node) -> dict:
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
    }
