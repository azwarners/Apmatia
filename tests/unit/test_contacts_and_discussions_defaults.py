import importlib


def test_participant_model_defaults_turn_policy_to_round_robin():
    models = importlib.import_module("apmatia.modules.contacts_and_discussions.models")
    importlib.reload(models)

    participant = models.DiscussionParticipant()

    assert participant.turn_policy == "round_robin"


def test_participant_view_schema_defaults_turn_policy_to_round_robin():
    collections = importlib.import_module("apmatia.modules.contacts_and_discussions.collections")
    importlib.reload(collections)

    participant_field = next(
        field
        for field in collections.PARTICIPANT_VIEW_SPEC.schema["fields"]
        if field["key"] == "turn_policy"
    )

    assert participant_field["default"] == "round_robin"
