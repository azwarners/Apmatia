from __future__ import annotations

from functools import lru_cache

from apmatia.modules.ai_model_manager.services import (
    create_llm_config,
    delete_llm_config,
    get_llm_config,
    list_llm_configs,
    probe_llm_config,
    update_llm_config,
)


class _LLMConfigManager:
    """Backward-compatible wrapper for LLM config operations."""

    def list_configs(self):
        return list_llm_configs()

    def get_config(self, config_id):
        return get_llm_config(config_id)

    def create_config(self, config):
        return create_llm_config(config)

    def update_config(self, config_id, **updates):
        return update_llm_config(config_id, **updates)

    def delete_config(self, config_id):
        return delete_llm_config(config_id)

    def probe_config(self, config_id):
        return probe_llm_config(config_id)


@lru_cache(maxsize=1)
def get_llm_config_manager() -> _LLMConfigManager:
    return _LLMConfigManager()
