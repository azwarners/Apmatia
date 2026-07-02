import json

from apmatia.lib.user_management.auth import SessionManager


def test_session_manager_create_get_delete():
    sessions = SessionManager()

    created = sessions.create_session(user_id=1, username="nick")
    assert created.user_id == 1
    assert created.username == "nick"
    assert created.token

    loaded = sessions.get_session(created.token)
    assert loaded is not None
    assert loaded.user_id == 1

    assert sessions.delete_session(created.token) is True
    assert sessions.get_session(created.token) is None
    assert sessions.delete_session(created.token) is False


def test_session_manager_persists_sessions(tmp_path):
    storage_path = tmp_path / "sessions.json"
    sessions = SessionManager(storage_path)

    created = sessions.create_session(user_id=1, username="nick")

    reloaded = SessionManager(storage_path)
    loaded = reloaded.get_session(created.token)

    assert loaded is not None
    assert loaded.user_id == 1
    assert loaded.username == "nick"
    assert loaded.expires_at == created.expires_at


def test_session_manager_drops_expired_sessions(tmp_path):
    storage_path = tmp_path / "sessions.json"
    sessions = SessionManager(storage_path)

    created = sessions.create_session(user_id=1, username="nick")
    payload = json.loads(storage_path.read_text(encoding="utf-8"))
    payload[0]["expires_at"] = "2000-01-01T00:00:00+00:00"
    storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    reloaded = SessionManager(storage_path)
    assert reloaded.get_session(created.token) is None
