import importlib


def test_runtime_initializes_singletons_and_reuses_instances(tmp_path, monkeypatch):
    monkeypatch.setenv("APMATIA_HOME", str(tmp_path / "app"))
    monkeypatch.setenv("APMATIA_DATA_DIR", str(tmp_path / "data"))

    runtime = importlib.import_module("src.core.user_management_runtime")
    runtime = importlib.reload(runtime)

    user_manager_first = runtime.get_user_manager()
    group_manager_first = runtime.get_group_manager()
    session_manager_first = runtime.get_session_manager()

    user_manager_second = runtime.get_user_manager()
    group_manager_second = runtime.get_group_manager()
    session_manager_second = runtime.get_session_manager()

    assert user_manager_first is user_manager_second
    assert group_manager_first is group_manager_second
    assert session_manager_first is session_manager_second
    assert runtime.APP_DIR.exists()
    assert runtime.DATA_DIR.exists()
