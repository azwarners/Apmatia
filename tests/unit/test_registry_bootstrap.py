from __future__ import annotations

from unittest.mock import patch

from apmatia.core.registry import Registry, create_application_registry, get_application_registry, load_bundled_modules
from apmatia.core.registry import bootstrap


ARCHIVED_MODULE_IDS = {
    "agent_loops", "ai_host_management", "ai_model_executor", "dev_tools", "discuss",
    "knowledge_wiki", "memory_manager", "os_admin", "runtime_telemetry", "worksim",
}
SURVIVING_MODULE_IDS = {
    "agent_alarms", "agent_config", "agent_tools", "agents", "ai_model_manager",
    "apmatia_admin", "auth", "ipe", "logging", "persistence", "preferences", "users", "ysparr",
}


def _module_ids(registry: Registry) -> set[str]:
    return {module.module_id for module in registry.list_modules(include_development=True)}


def test_load_bundled_modules_excludes_archived_modules():
    registry = load_bundled_modules(Registry(), include_development=True)
    assert _module_ids(registry) == SURVIVING_MODULE_IDS
    assert not (_module_ids(registry) & ARCHIVED_MODULE_IDS)
    assert registry.list_actions()
    assert registry.list_commands()
    assert registry.list_views()


def test_create_application_registry_excludes_archived_modules():
    registry = create_application_registry(include_development=False)
    assert _module_ids(registry) == {"agents", "ai_model_manager", "auth", "logging", "persistence", "preferences", "users", "ysparr"}
    assert not (_module_ids(registry) & ARCHIVED_MODULE_IDS)


def test_stable_registry_excludes_all_development_contributions():
    registry = create_application_registry(include_development=False)
    assert _module_ids(registry) <= SURVIVING_MODULE_IDS
    assert all(item.module_id in SURVIVING_MODULE_IDS for item in registry.list_actions())
    assert all(item.module_id in SURVIVING_MODULE_IDS for item in registry.list_tools())
    assert all(item.module_id in SURVIVING_MODULE_IDS for item in registry.list_commands())
    assert all(item.module_id in SURVIVING_MODULE_IDS for item in registry.list_views())


def test_get_application_registry_returns_cached_registry():
    bootstrap.get_application_registry.cache_clear()
    with patch("apmatia.core.registry.bootstrap.get_config_value", return_value=False):
        first = get_application_registry()
        second = get_application_registry()
    assert first is second
    assert _module_ids(first) == {"agents", "ai_model_manager", "auth", "logging", "persistence", "preferences", "users", "ysparr"}
