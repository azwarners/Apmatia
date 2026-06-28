"""Internal API for memory management."""

from src.core.memory_management_runtime import get_memory_manager


def create_memory(title: str, content: str, **kwargs) -> dict:
    memory = get_memory_manager().create_memory(title, content, **kwargs)
    return _memory_to_dict(memory)


def get_memory(memory_id: int, **kwargs) -> dict | None:
    memory = get_memory_manager().get_memory(memory_id, **kwargs)
    if memory is None:
        return None
    return _memory_to_dict(memory)


def update_memory(memory_id: int, **updates) -> dict:
    memory = get_memory_manager().update_memory(memory_id, **updates)
    return _memory_to_dict(memory)


def search_memories(query: str, **kwargs) -> list[dict]:
    return [_memory_to_dict(memory) for memory in get_memory_manager().search_memories(query, **kwargs)]


def list_memories(**kwargs) -> list[dict]:
    return [_memory_to_dict(memory) for memory in get_memory_manager().list_memories(**kwargs)]


def archive_memory(memory_id: int, **kwargs) -> dict:
    memory = get_memory_manager().archive_memory(memory_id, **kwargs)
    return _memory_to_dict(memory)


def delete_memory(memory_id: int, **kwargs) -> dict:
    memory = get_memory_manager().delete_memory(memory_id, **kwargs)
    return _memory_to_dict(memory)


def _memory_to_dict(memory) -> dict:
    return {
        "id": memory.id,
        "title": memory.title,
        "content": memory.content,
        "tags": list(memory.tags),
        "owner_user_id": memory.owner_user_id,
        "owner_group_id": memory.owner_group_id,
        "owner_agent_id": memory.owner_agent_id,
        "mode": memory.mode,
        "created_by_agent_id": memory.created_by_agent_id,
        "source_discussion_id": memory.source_discussion_id,
        "source_message_ids": list(memory.source_message_ids),
        "visibility": memory.visibility,
        "status": memory.status,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
    }
