from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


# These existing behavior tests are the minimum parity gate for replacing the corresponding custom
# Streamlit paths. Tests may be strengthened or replaced with renderer-neutral equivalents, but a
# baseline entry cannot disappear until its migration phase explicitly supersedes it.
PARITY_BASELINE: dict[str, tuple[str, ...]] = {
    "generic_module_views": (
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_routes_contract_ready_view_through_api_document",
        "tests/unit/test_streamlit_contract_renderer.py::test_contract_renderer_renders_form_and_emits_portable_intent",
        "tests/unit/test_streamlit_contract_renderer.py::test_contract_renderer_initializes_state_evaluates_conditions_and_applies_effects",
        "tests/unit/test_phase2_generic_views.py::test_portable_controller_loads_declared_module_view_data_source",
        "tests/unit/test_phase2_generic_views.py::test_portable_controller_executes_serialized_create_action",
        "tests/unit/test_phase2_generic_views.py::test_portable_controller_prefills_and_executes_serialized_edit_action",
        "tests/unit/test_phase2_generic_views.py::test_portable_controller_confirms_serialized_item_action",
    ),
    "agent_config_alarms_and_hosts": (
        "tests/unit/test_streamlit_module_views.py::test_agent_config_document_exposes_portable_per_agent_edit",
        "tests/unit/test_phase3_management_views.py::test_agent_config_provider_accepts_generic_item_identity",
        "tests/unit/test_streamlit_module_views.py::test_agent_alarm_document_declares_dropdown_sources_and_schedule_fields",
        "tests/unit/test_phase3_management_views.py::test_portable_alarm_sources_project_api_items_to_options",
        "tests/unit/test_phase3_management_views.py::test_ai_host_documents_are_contract_ready_with_executable_form_actions",
    ),
    "agents": (
        "tests/unit/test_phase3_management_views.py::test_agents_management_is_a_portable_crud_document",
    ),
    "users_and_groups": (
        "tests/unit/test_phase3_management_views.py::test_users_groups_and_memberships_are_a_portable_crud_document",
        "tests/unit/test_users_module_views.py::test_users_view_commands_enforce_account_and_group_ownership",
    ),
    "module_management": (
        "tests/unit/test_phase3_management_views.py::test_module_management_is_a_portable_catalog_document",
        "tests/unit/test_preferences_module_management.py::test_preferences_provider_updates_view_order",
    ),
    "discussion_and_contacts": (
        "tests/unit/test_streamlit_discussion_baseline.py::test_discussion_document_requires_an_agent_before_chatting",
        "tests/unit/test_streamlit_discussion_baseline.py::test_discussion_document_preserves_active_streaming_timeline_semantics",
        "tests/unit/test_streamlit.py::test_contacts_shell_creates_fresh_discussion_for_agent_contact",
        "tests/unit/test_streamlit.py::test_contacts_shell_reopens_existing_discussion_for_agent_contact",
        "tests/unit/test_streamlit.py::test_contacts_shell_creates_fresh_discussion_for_group_contact",
        "tests/unit/test_streamlit.py::test_contacts_shell_reopens_existing_discussion_for_group_contact",
        "tests/unit/test_streamlit.py::test_contacts_sidebar_filters_to_selected_group_members_and_highlights_current_speaker",
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_creates_participant_for_agent_target",
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_creates_fresh_group_discussion_from_participant_view",
    ),
    "agent_loops": (
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_renders_agent_loops_shell_with_sidebar_and_tabs",
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_starts_agent_loops_task_from_form",
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_stops_agent_loops_task_from_history",
        "tests/unit/test_streamlit_module_views.py::test_agent_loop_live_output_is_append_only_and_ignores_streaming_fragments",
        "tests/unit/test_streamlit_module_views.py::test_module_views_page_renders_agent_loops_task_history_as_terminal_stack",
        "tests/unit/test_streamlit_module_views.py::test_agent_loop_task_progress_redraws_checklist_and_status",
    ),
}


def test_view_extraction_parity_baseline_references_real_tests():
    missing: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for references in PARITY_BASELINE.values():
        for reference in references:
            if reference in seen:
                duplicates.append(reference)
            seen.add(reference)
            path_text, test_name = reference.split("::", maxsplit=1)
            path = REPO_ROOT / path_text
            if not path.is_file() or test_name not in _top_level_test_functions(path):
                missing.append(reference)
    assert duplicates == []
    assert missing == []


def _top_level_test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    }
