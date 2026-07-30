import importlib
from pathlib import Path


def test_discuss_database_keeps_existing_legacy_data(tmp_path: Path):
    services = importlib.import_module("apmatia.modules.discuss.services")
    legacy_database = tmp_path / "contacts_and_discussions.db"
    legacy_database.touch()

    assert services._resolve_discuss_db(tmp_path) == legacy_database


def test_discuss_database_prefers_renamed_database(tmp_path: Path):
    services = importlib.import_module("apmatia.modules.discuss.services")
    legacy_database = tmp_path / "contacts_and_discussions.db"
    legacy_database.touch()
    database = tmp_path / "discuss.db"
    database.touch()

    assert services._resolve_discuss_db(tmp_path) == database


def test_participant_model_defaults_turn_policy_to_round_robin():
    models = importlib.import_module("apmatia.modules.discuss.models")
    importlib.reload(models)

    participant = models.DiscussionParticipant()

    assert participant.turn_policy == "round_robin"


def test_participant_view_schema_defaults_turn_policy_to_round_robin():
    collections = importlib.import_module("apmatia.modules.discuss.collections")
    importlib.reload(collections)

    participant_field = next(
        field
        for field in collections.PARTICIPANT_VIEW_SPEC.schema["fields"]
        if field["key"] == "turn_policy"
    )

    assert participant_field["default"] == "round_robin"
