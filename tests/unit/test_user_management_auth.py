from src.core.user_management.auth import SessionManager


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

