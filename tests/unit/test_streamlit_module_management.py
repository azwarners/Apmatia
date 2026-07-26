from __future__ import annotations

import importlib
from unittest.mock import patch


def _catalog(*modules: dict[str, object], show_development_modules: bool = False) -> list[dict[str, object]]:
    return [
        {
            "id": "module_catalog",
            "show_development_modules": show_development_modules,
            "modules": list(modules),
        }
    ]


def _module(*, views: list[dict[str, object]] | None = None) -> dict[str, object]:
    resolved_views = list(views or [])
    return {
        "module_id": "ipe",
        "name": "Integrated Productivity Environment",
        "version": "0.1.0",
        "description": "Personal productivity tools.",
        "hidden": False,
        "view_count": len(resolved_views),
        "visible_view_count": sum(not bool(view.get("effective_hidden")) for view in resolved_views),
        "views": resolved_views,
    }


def _load_renderer():
    import apmatia.interfaces.streamlit.module_views.module_manager as module_manager_view

    return importlib.reload(module_manager_view)


def test_module_manager_view_lists_modules_and_views(mock_streamlit):
    items = _catalog(
        _module(
            views=[
                {
                    "view_id": "ipe.task.view",
                    "name": "Tasks View",
                    "description": "Task collection.",
                    "hidden": False,
                    "effective_hidden": False,
                },
                {
                    "view_id": "ipe.project.view",
                    "name": "Projects View",
                    "description": "Project collection.",
                    "hidden": True,
                    "effective_hidden": True,
                },
            ]
        )
    )

    _load_renderer().render(items)

    mock_streamlit.title.assert_called_with("Module Manager")
    mock_streamlit.subheader.assert_any_call("Integrated Productivity Environment")
    mock_streamlit.write.assert_any_call("Tasks View")
    mock_streamlit.write.assert_any_call("Projects View")


def test_module_manager_view_toggles_module_visibility(mock_streamlit):
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide module"
    renderer = _load_renderer()

    with patch.object(renderer, "execute_module_command") as execute:
        renderer.render(_catalog(_module()))

    execute.assert_called_once_with(
        "module_manager.set_module_visibility",
        module_id="ipe",
        hidden=True,
    )
    mock_streamlit.rerun.assert_called_once()


def test_module_manager_view_reorders_modules(mock_streamlit):
    second = {**_module(), "module_id": "worksim", "name": "Worksim"}
    mock_streamlit.button.side_effect = lambda label, **kwargs: label == "Move down" and not kwargs.get("disabled", False)
    renderer = _load_renderer()

    with patch.object(renderer, "execute_module_command") as execute:
        renderer.render(_catalog(_module(), second))

    execute.assert_called_once_with(
        "module_manager.set_module_order",
        module_id="ipe",
        new_index=1,
    )
    mock_streamlit.rerun.assert_called_once()


def test_module_manager_view_toggles_view_visibility(mock_streamlit):
    view = {
        "view_id": "ipe.task.view",
        "name": "Tasks View",
        "description": "",
        "hidden": False,
        "effective_hidden": False,
    }
    mock_streamlit.button.side_effect = lambda label, **_kwargs: label == "Hide view"
    renderer = _load_renderer()

    with patch.object(renderer, "execute_module_command") as execute:
        renderer.render(_catalog(_module(views=[view])))

    execute.assert_called_once_with(
        "module_manager.set_view_visibility",
        view_id="ipe.task.view",
        hidden=True,
    )
    mock_streamlit.rerun.assert_called_once()


def test_module_manager_view_enables_all_modules(mock_streamlit):
    mock_streamlit.toggle.side_effect = None
    mock_streamlit.toggle.return_value = True
    renderer = _load_renderer()

    with patch.object(renderer, "execute_module_command") as execute:
        renderer.render(_catalog())

    execute.assert_called_once_with(
        "module_manager.set_activation",
        enabled=True,
    )
    mock_streamlit.rerun.assert_called_once()
