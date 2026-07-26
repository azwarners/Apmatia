from __future__ import annotations

from apmatia.core.module_view_runtime import ModuleViewContext
from apmatia.core.registry import CommandContribution, ViewContribution
from apmatia.modules.ipe.module_views import ApmatiaIpeModuleViewProvider
from apmatia.modules.ipe.services import ApmatiaIpeService
from apmatia.modules.ipe.sqlite_repositories import SQLiteIpeBundle


def test_ipe_module_view_provider_creates_and_lists_ideas(tmp_path):
    service = ApmatiaIpeService(SQLiteIpeBundle(tmp_path / "ipe.db"))
    provider = ApmatiaIpeModuleViewProvider(service)
    context = ModuleViewContext(user_id=7)
    command = CommandContribution(
        module_id="ipe",
        command_id="ipe.idea.create",
        name="Create idea",
        metadata={
            "object_type": "idea",
            "verb": "create",
            "collection_view_id": "ipe.idea.view",
        },
    )
    view = ViewContribution(
        module_id="ipe",
        action_id="ipe.idea",
        view_id="ipe.idea.view",
        name="Ideas View",
        metadata={"object_type": "idea"},
    )

    created = provider.execute_command(
        command=command,
        payload={"title": "Capture this", "body": "Important thought", "tags": "ideas, inbox"},
        context=context,
    )
    items = provider.list_items(view=view, context=context)

    assert created is not None
    assert created["status"] == "created"
    assert created["item"]["title"] == "Capture this"
    assert created["item"]["tags"] == ["ideas", "inbox"]
    assert [item["title"] for item in items] == ["Capture this"]
