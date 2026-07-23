from __future__ import annotations

import importlib


def test_import_apmatia_package_and_moved_libraries():
    package = importlib.import_module("apmatia")
    model_management = importlib.import_module("apmatia.modules.ai_model_manager")

    assert package.__name__ == "apmatia"
    assert model_management.__name__ == "apmatia.modules.ai_model_manager"
