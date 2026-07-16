from __future__ import annotations

import importlib


def test_sync_page_generation_advances_only_when_selected_page_changes(mock_streamlit):
    import apmatia.interfaces.streamlit.page_runtime as page_runtime

    page_runtime = importlib.reload(page_runtime)

    assert page_runtime.sync_page_generation("discussion") == 1
    assert page_runtime.current_page_generation() == 1
    assert page_runtime.is_current_page_generation(1) is True

    assert page_runtime.sync_page_generation("discussion") == 1
    assert page_runtime.current_page_generation() == 1
    assert page_runtime.is_current_page_generation(1) is True

    assert page_runtime.sync_page_generation("module_view") == 2
    assert page_runtime.current_page_generation() == 2
    assert page_runtime.is_current_page_generation(1) is False
    assert page_runtime.is_current_page_generation(2) is True


def test_sync_page_generation_advances_when_module_view_detail_changes(mock_streamlit):
    import apmatia.interfaces.streamlit.page_runtime as page_runtime

    page_runtime = importlib.reload(page_runtime)

    assert page_runtime.sync_page_generation("module_view", detail="agent_loops:agent_loops.tasks.view") == 1
    assert page_runtime.current_page_generation() == 1

    assert page_runtime.sync_page_generation("module_view", detail="agent_loops:agent_loops.contacts.view") == 2
    assert page_runtime.current_page_generation() == 2
    assert page_runtime.is_current_page_generation(1) is False
    assert page_runtime.is_current_page_generation(2) is True


def test_sync_page_generation_initializes_blank_pages_without_advancing(mock_streamlit):
    import apmatia.interfaces.streamlit.page_runtime as page_runtime

    page_runtime = importlib.reload(page_runtime)

    assert page_runtime.sync_page_generation("") == 0
    assert page_runtime.current_page_generation() == 0
    assert page_runtime.sync_page_generation("") == 0
    assert page_runtime.current_page_generation() == 0
    assert page_runtime.sync_page_generation("discussion") == 1
    assert page_runtime.current_page_generation() == 1
