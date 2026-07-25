"""
Tests for the complete authentication flow: user registration followed by login/session creation.
"""
from apmatia.modules.users.auth import SessionManager
from apmatia.modules.users.manager import UserManager
from apmatia.modules.users.sqlite_repositories import SQLiteUserManagementBundle


def _bundle(tmp_path):
    db_path = tmp_path / "users.db"
    return SQLiteUserManagementBundle(db_path)


def test_register_and_authenticate_user(tmp_path):
    """Test the complete flow: register a new user, then authenticate with session creation."""
    bundle = _bundle(tmp_path)
    users = UserManager(bundle.users)
    sessions = SessionManager()

    # Step 1: Register a new user
    registered = users.create_user("alice", "secret123")
    assert registered.id is not None
    assert registered.username == "alice"

    # Step 2: Verify credentials work
    assert users.verify_user("alice", "secret123") is True
    assert users.verify_user("alice", "wrongpass") is False

    # Step 3: Create an authenticated session after successful verification
    if users.verify_user("alice", "secret123"):
        session = sessions.create_session(user_id=registered.id, username="alice")
        assert session.token is not None
        assert session.user_id == registered.id
        assert session.username == "alice"

    # Step 4: Retrieve the session
    retrieved = sessions.get_session(session.token)
    assert retrieved is not None
    assert retrieved.user_id == registered.id
    assert retrieved.username == "alice"

    # Step 5: Clean up session
    assert sessions.delete_session(session.token) is True
    assert sessions.get_session(session.token) is None


def test_register_multiple_users_and_authenticate(tmp_path):
    """Test registering multiple users and authenticating each independently."""
    bundle = _bundle(tmp_path)
    users = UserManager(bundle.users)
    sessions = SessionManager()

    # Register two users
    user1 = users.create_user("bob", "pass1")
    user2 = users.create_user("carol", "pass2")

    # Create sessions for both
    session1 = sessions.create_session(user_id=user1.id, username="bob")
    session2 = sessions.create_session(user_id=user2.id, username="carol")

    # Verify sessions are independent
    assert sessions.get_session(session1.token).user_id == user1.id
    assert sessions.get_session(session2.token).user_id == user2.id
    assert session1.token != session2.token

    # Clean up
    assert sessions.delete_session(session1.token) is True
    assert sessions.delete_session(session2.token) is True
    assert sessions.get_session(session1.token) is None
    assert sessions.get_session(session2.token) is None


def test_authentication_fails_for_disabled_user(tmp_path):
    """Test that authentication fails for a user that has been disabled."""
    bundle = _bundle(tmp_path)
    users = UserManager(bundle.users)
    sessions = SessionManager()

    # Register and disable a user
    user = users.create_user("dave", "pass1")
    users.set_user_enabled(user.id, enabled=False)

    # Verify authentication fails
    assert users.verify_user("dave", "pass1") is False

    # Even if we try to create a session manually, the verification step would fail
    session = sessions.create_session(user_id=user.id, username="dave")
    assert session.username == "dave"
    assert users.verify_user("dave", "pass1") is False

    sessions.delete_session(session.token)
