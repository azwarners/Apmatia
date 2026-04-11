from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from src.api.http.app import app


client = TestClient(app)


@patch("src.api.http.routes.create_user")
def test_api_create_user(mock_create_user):
    mock_create_user.return_value = {"id": 1, "username": "nick"}

    response = client.post("/api/users", json={"username": "nick", "password": "pw"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "created",
        "user": {"id": 1, "username": "nick"},
    }
    mock_create_user.assert_called_once_with(username="nick", password="pw")


@patch("src.api.http.routes.verify_user")
def test_api_verify_user(mock_verify_user):
    mock_verify_user.return_value = True

    response = client.post("/api/users/verify", json={"username": "nick", "password": "pw"})

    assert response.status_code == 200
    assert response.json() == {"valid": True}
    mock_verify_user.assert_called_once_with(username="nick", password="pw")


@patch("src.api.http.routes.edit_user")
def test_api_edit_user(mock_edit_user):
    mock_edit_user.return_value = {"id": 1, "username": "nick-updated", "is_enabled": True}

    response = client.patch("/api/users/1", json={"username": "nick-updated", "is_enabled": True})

    assert response.status_code == 200
    assert response.json() == {
        "status": "updated",
        "user": {"id": 1, "username": "nick-updated", "is_enabled": True},
    }
    mock_edit_user.assert_called_once_with(
        user_id=1,
        username="nick-updated",
        password=None,
        is_enabled=True,
    )


@patch("src.api.http.routes.delete_user")
def test_api_delete_user(mock_delete_user):
    mock_delete_user.return_value = True

    response = client.delete("/api/users/1")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
    mock_delete_user.assert_called_once_with(user_id=1)


@patch("src.api.http.routes.list_users")
def test_api_list_users(mock_list_users):
    mock_list_users.return_value = [{"id": 1, "username": "nick"}]

    response = client.get("/api/users")

    assert response.status_code == 200
    assert response.json() == {"users": [{"id": 1, "username": "nick"}]}
    mock_list_users.assert_called_once_with()


@patch("src.api.http.routes.create_group")
def test_api_create_group(mock_create_group):
    mock_create_group.return_value = {"id": 10, "name": "team"}

    response = client.post(
        "/api/groups",
        json={"name": "team", "created_by_user_id": 1, "description": "core team"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "created", "group": {"id": 10, "name": "team"}}
    mock_create_group.assert_called_once_with(
        name="team",
        created_by_user_id=1,
        description="core team",
    )


@patch("src.api.http.routes.delete_group")
def test_api_delete_group(mock_delete_group):
    mock_delete_group.return_value = True

    response = client.delete("/api/groups/10")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
    mock_delete_group.assert_called_once_with(group_id=10)


@patch("src.api.http.routes.list_groups")
def test_api_list_groups(mock_list_groups):
    mock_list_groups.return_value = [{"id": 10, "name": "team"}]

    response = client.get("/api/groups")

    assert response.status_code == 200
    assert response.json() == {"groups": [{"id": 10, "name": "team"}]}
    mock_list_groups.assert_called_once_with()


@patch("src.api.http.routes.add_member")
def test_api_add_member(mock_add_member):
    mock_add_member.return_value = {"id": 100, "group_id": 10, "user_id": 1, "role": "member"}

    response = client.post("/api/groups/10/members", json={"user_id": 1, "role": "member"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "created",
        "membership": {"id": 100, "group_id": 10, "user_id": 1, "role": "member"},
    }
    assert mock_add_member.call_count == 1


@patch("src.api.http.routes.create_user")
def test_api_user_management_not_implemented_maps_to_501(mock_create_user):
    mock_create_user.side_effect = NotImplementedError

    response = client.post("/api/users", json={"username": "nick", "password": "pw"})

    assert response.status_code == 501
    assert response.json()["detail"] == "User management not implemented yet."


@patch("src.api.http.routes.create_group")
def test_api_group_management_not_implemented_maps_to_501(mock_create_group):
    mock_create_group.side_effect = NotImplementedError

    response = client.post(
        "/api/groups",
        json={"name": "team", "created_by_user_id": 1, "description": ""},
    )

    assert response.status_code == 501
    assert response.json()["detail"] == "Group management not implemented yet."
