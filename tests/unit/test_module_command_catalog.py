from __future__ import annotations

from apmatia.api.internal.module_views import list_module_commands


def test_active_module_command_catalog_is_self_describing():
    catalog = list_module_commands()
    agents_create = next(item for item in catalog if item["command_id"] == "agents.create")
    model_create = next(item for item in catalog if item["command_id"] == "ai_model_manager.models.create")

    assert agents_create["path"] == ["agents", "create"]
    assert agents_create["module_name"] == "Agents"
    assert agents_create["description"]
    assert "action_id" not in agents_create
    assert isinstance(agents_create["fields"], list)
    assert any(field["key"] == "name" for field in model_create["fields"])
