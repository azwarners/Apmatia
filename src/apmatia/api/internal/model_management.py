from __future__ import annotations

from apmatia.core.model_management_runtime import get_llm_config_manager
from apmatia.modules.ai_model_manager.models import LLMConfig


def _llm_config_to_dict(config: LLMConfig) -> dict:
    return {
        "id": config.id,
        "user_alias": config.user_alias,
        "metadata": dict(config.metadata),
        "backend": config.backend,
        "provider_name": config.provider_name,
        "model_url": config.model_url,
        "api_key": config.api_key,
        "max_response_size": config.max_response_size,
        "system_prompt": config.system_prompt,
    }


def list_llm_configs() -> list[dict]:
    manager = get_llm_config_manager()
    return [_llm_config_to_dict(config) for config in manager.list_configs()]


def create_llm_config(**payload) -> dict:
    manager = get_llm_config_manager()
    config = manager.create_config(LLMConfig(**payload))
    return _llm_config_to_dict(config)


def update_llm_config(config_id: int, **updates) -> dict:
    manager = get_llm_config_manager()
    config = manager.update_config(config_id, **updates)
    return _llm_config_to_dict(config)


def delete_llm_config(config_id: int) -> bool:
    manager = get_llm_config_manager()
    return manager.delete_config(config_id)


def test_llm_config(config_id: int) -> dict:
    manager = get_llm_config_manager()
    return manager.probe_config(config_id)


def get_llm_config(config_id: int) -> dict | None:
    manager = get_llm_config_manager()
    config = manager.get_config(config_id)
    if config is None:
        return None
    return _llm_config_to_dict(config)
