from __future__ import annotations

import json
import subprocess
import sys

from apmatia.core.registry import create_application_registry
from apmatia.core.view_contract import normalize_view_document, validate_view_document


# SHA-256 snapshots cover the complete canonical JSON document for every bundled registered view.
# The subprocess that produces them blocks Streamlit imports before any Apmatia package is loaded.
REGISTERED_VIEW_DOCUMENT_SNAPSHOTS = {
    "agent_alarms.alarms.view": "7642554b2ba7c3e7f7fb61add68856dbfa0d482d650b32b590895eb843c6712f",
    "agent_config.agent_config.view": "72855c1744f61b6fec7a8eee437c112f1e35ee7f8d82b5a572ee06518f60a9b8",
    "agent_loops.contacts.view": "ffc26b30bb4ceeb75af455ec3c1bf4538de5d4849c63064234d8eae16b250150",
    "agent_loops.knowledge.view": "6cc5138f8e649e6d8f5876982184a83844409b789058aed845211e138a441558",
    "agent_loops.loops.view": "a4316eae3edf7abb60441ec819569dd3c8df0d1f9a7a038f006330de5cb5f09d",
    "agent_loops.tasks.view": "d6e4e3c0f1238bd8ba105cdbdc61ea845068cf4f950038a2f324e72b1f7f3a02",
    "agent_loops.workspace.view": "0e379a43544c06e6a6cb28281b6f65d3f6182c4cbea5d60e6329444437108805",
    "agent_tools.agent_tools.view": "df6b3e21f09da075b0c423f62dc88049a7da9a68768c244b304f60ff87aadf6d",
    "agents.agents.view": "83e28d3e581d09b8fccf36c212a5bf3d2c9b9c007e488fa6248177fcb4ea8630",
    "ai_host_management.hosts.view": "425a91801ca9914a4da9c3c95706bc1c6a51fb6642dc40874a68725987771b80",
    "ai_host_management.resources.view": "d1e57c31edc261f33229086d909ad4b0a0ee102cfe170c708518a7a9f7100f25",
    "ai_model_executor.capacity.view": "6088f135c484a7da273b0ec85405fa00ab3e7658f24bde9affd7de725efce611",
    "ai_model_executor.executions.view": "ad4660e717897c46d1dc5fe40cc1ebedc4ce713bcea2c7ebba26453e2d805cc1",
    "ai_model_executor.queue.view": "48f5e2b931dd04e41fad74bb4210be1fa9ed9dd53ba4a36f57c925907ee02463",
    "ai_model_executor.reservations.view": "66da95798166518caac3d6b503014e6cd1a1fb17a8cb73db3c573b9aa7112697",
    "ai_model_executor.resources.view": "62971c970d59f22e5cb12860db6b94b8264338502144282f1eb4cbbe464caede",
    "ai_model_manager.llm_configs.view": "25a243db8bbda3fb744f85a2c83a8a84f76e45a295965e87eea41fa2588fe3cd",
    "ai_model_manager.models.view": "fc1e820715583ceebd14e746eec22921f1a2ce3ba0b9351933d2fab3601741c3",
    "ai_model_manager.preferences.view": "10ba4da5d45ab389decd8df17b5b4dc2179f3a78598b0c8c2034d5e4bb05da01",
    "auth.login.view": "00f83792aab1ce25fc3b0c136594007c007e546eda1e8c836fa6bf7f8d9b2db5",
    "auth.register.view": "656fb2da2f83549fb58040f12d54f6391cd812b37adc775ee952dc032a204a13",
    "discuss.chat_targets.view": "ea8b7762d3df60772be19d1d91d0e19e28d95e94235c4c15086fb1d76f7f7c6a",
    "discuss.discussion.view": "7ede4989f2b13c11e060e302f5b231eb60eeaa6aaadc60588af895bc8b389868",
    "ipe.calendar_event.view": "4a01108e14d0d397c36e762da12a070ac6359aec83f4f3531e36df04d34904b8",
    "ipe.habit.view": "312fae69b15f9ab8b4a984738a93e965c94586e6671b103410b18531e853c30f",
    "ipe.idea.view": "8812f847dfe44f93a05c655725693158e005ab1103d820a60d05b7c65faf89fb",
    "ipe.project.view": "6b4750090421768d847c59f508931dab147c2f937a665f4e6c9aaf2e5d1cf07f",
    "ipe.task.view": "fa88cbc88e34c3e28f25b6ed9c2f371147e49caf8751ababb4970fd65d51b253",
    "logging.entries.view": "745bf8e1b3813dae76bcdc3835239e054711ca272c28c5eb843a7423c41f9daa",
    "memory_manager.memory.view": "0cbdbf64a9ae51b942e394ab35e72988c622f412836edd3a43346de110552676",
    "preferences.modules.view": "24aa8ec02d179b78e2a78f38c2063b982b684067c59b15c03dd2834f7d16999f",
    "preferences.preferences.view": "140640d28d535c5136f0388129af773e8f7fb3967b522ba18f3b6d0684929637",
    "users.users.view": "fb3c04572f305f340a155e53ba4144e70de464b6ed2162f19f34f2303becd93b",
    "worksim.org_chart_node.view": "16c899d4ec0dfe7d5c6f4bc6db3f8d66194b71c164f609aa3e37b8cc45b8d6e3",
}


def test_every_registered_view_validates_and_round_trips_with_view_context():
    registry = create_application_registry(include_development=True)

    for view in registry.list_views():
        try:
            document = normalize_view_document(view)
            validate_view_document(document)
            assert json.loads(json.dumps(document.to_dict())) == document.to_dict()
        except Exception as error:
            raise AssertionError(f"{view.view_id}: contract validation failed: {error}") from error

        if view.metadata.get("presentation") is not None:
            assert document.metadata.get("legacy") is not True, view.view_id


def test_all_registered_view_documents_are_api_serializable_without_streamlit():
    code = r'''
import builtins
import hashlib
import json

original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise AssertionError("streamlit import attempted")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import

from apmatia.api.internal import module_views
from apmatia.core.registry import create_application_registry

registry = create_application_registry(include_development=True)
module_views.get_application_registry = lambda: registry
documents = module_views.list_module_view_documents()
assert documents
assert [document["view_id"] for document in documents] == sorted(
    document["view_id"] for document in documents
)
assert all(document["schema_version"] == 1 for document in documents)
assert json.loads(json.dumps(documents)) == documents

snapshots = {
    document["view_id"]: hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    for document in documents
}
print(json.dumps(snapshots, sort_keys=True))
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == REGISTERED_VIEW_DOCUMENT_SNAPSHOTS
