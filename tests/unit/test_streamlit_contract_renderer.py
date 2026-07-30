from __future__ import annotations

import importlib


def _form_document() -> dict:
    return {
        "schema_version": 1,
        "view_id": "auth.login.view",
        "module_id": "auth",
        "title": "Sign In",
        "description": "Use your account.",
        "state": [{"key": "notice", "default": "", "scope": "view", "value_type": "string"}],
        "actions": [
            {
                "key": "login",
                "intent": "save",
                "label": "Sign In",
                "scope": "view",
                "style": "primary",
                "operation": "legacy_intent",
                "payload": {"auth_action": "login"},
                "success_effects": [],
                "failure_effects": [],
            }
        ],
        "data_sources": [],
        "presentation": {
            "component_id": "login-page",
            "component_type": "page",
            "properties": {"caption": "Welcome.", "render_mode": "form"},
            "children": [
                {
                    "component_id": "login-form",
                    "component_type": "form",
                    "properties": {"key": "login", "title": "Sign In", "submit_label": "Sign In"},
                    "children": [
                        {
                            "component_id": "username",
                            "component_type": "field",
                            "properties": {"key": "username", "label": "Username", "field_type": "text"},
                        },
                        {
                            "component_id": "password",
                            "component_type": "field",
                            "properties": {"key": "password", "label": "Password", "field_type": "password"},
                        },
                    ],
                }
            ],
        },
    }


def test_contract_renderer_renders_form_and_emits_portable_intent(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.contract_renderer as renderer

    renderer = importlib.reload(renderer)
    mock_streamlit.text_input.side_effect = ["nick", "secret"]

    intents = renderer.render_view_document(_form_document())

    assert intents == [
        {
            "view_id": "auth.login.view",
            "intent": "save",
            "action_key": "login",
            "scope": "view",
            "item_id": None,
            "item": None,
            "payload": {"auth_action": "login", "operation": "legacy_intent", "username": "nick", "password": "secret"},
        }
    ]
    mock_streamlit.title.assert_called_once_with("Sign In")
    mock_streamlit.caption.assert_any_call("Welcome.")


def test_contract_renderer_initializes_state_evaluates_conditions_and_applies_effects(mock_streamlit):
    import apmatia.interfaces.streamlit.module_views.contract_renderer as renderer

    renderer = importlib.reload(renderer)
    document = _form_document()
    state = renderer.initialize_view_state(document)

    assert state == {"notice": ""}
    assert renderer.evaluate_condition(
        {
            "operator": "all",
            "operands": [
                {"operator": "equals", "operands": [{"source": "items", "path": "0.status"}, "ready"]},
                {"operator": "falsy", "operands": [{"source": "notice", "path": ""}]},
            ],
        },
        data_sources={"items": [{"status": "ready"}]},
        state=state,
    )

    refresh = renderer.apply_effects(
        document,
        [
            {"effect_type": "set_state", "target": "notice", "source": "result.message"},
            {"effect_type": "show_notification", "value": "Saved"},
            {"effect_type": "refresh_source", "target": "items"},
        ],
        result={"message": "Complete"},
    )

    assert refresh is True
    assert state["notice"] == "Complete"
    mock_streamlit.success.assert_called_once_with("Saved")
