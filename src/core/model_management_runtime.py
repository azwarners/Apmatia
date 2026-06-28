from __future__ import annotations

from functools import lru_cache

from src.lib.model_management import LLMManager


@lru_cache(maxsize=1)
def get_llm_config_manager() -> LLMManager:
    return LLMManager()
