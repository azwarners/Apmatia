"""User and group management page for Apmatia."""
from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from src.interfaces.streamlit.api_client import (
    ApiError,
    add_group_member,
    create_group,
    create_user,
    delete_group,
    delete_user,
    list_group_members,
    list_groups,
    list_users,
    set_group_membership_enabled,
    update_group,
    update_user,
)


def _safe_int(value: object) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _current_user_id() -> int | None:
    authenticated_user = st.session_state.get("authenticated_user")
    if not isinstance(authenticated_user, dict):
        return None
    return _safe_int(authenticated_user.get("user_id"))


def _user_label(user: dict[str, object]) -> str:
    return f"{user.get('username') or 'Unnamed user'} (ID {user.get('id')})"


def _group_label(group: dict[str, object]) -> str:
    return f"{group.get('name') or 'Unnamed group'} (ID {group.get('id')})"


def _group_is_owned_by_current_user(group: dict[str, object], current_user_id: int | None) -> bool:
    if current_user_id is None:
        return False
    return _safe_int(group.get("created_by_user_id")) == current_user_id


def _selected_index(options: list[object], selected_value: object) -> int:
    if selected_value in options:
        return options.index(selected_value)
    return 0


def _user_form_defaults(user: dict[str, object] | None) -> dict[str, object]:
    return {
        "id": None if user is None else user.get("id"),
        "username": "" if user is None else user.get("username", ""),
        "password": "",
        "is_enabled": True if user is None else bool(user.get("is_enabled", True)),
    }


def _group_form_defaults(group: dict[str, object] | None) -> dict[str, object]:
    return {
        "id": None if group is None else group.get("id"),
        "name": "" if group is None else group.get("name", ""),
        "description": "" if group is None else group.get("description", ""),
    }


def _list_group_members_safe(group_id: int) -> list[dict[str, object]]:
    try:
        return list_group_members(group_id)
    except ApiError:
        return []


def _current_user(users: Iterable[dict[str, object]]) -> dict[str, object] | None:
    user_id = _current_user_id()
    if user_id is None:
        return None
    for user in users:
        if not isinstance(user, dict):
            continue
        if _safe_int(user.get("id")) == user_id:
            return user
    return None


def render() -> None:
    """Render the user and group management page."""
    try:
        users = list_users()
        groups = list_groups()
    except ApiError as error:
        st.error(f"Unable to load user management data: {error.detail}")
        return

    current_user_id = _current_user_id()

    st.title("User Management")
    st.caption("Create users, edit your account, and manage the groups you own through the local API.")

    if "user_management_user_form" not in st.session_state:
        st.session_state["user_management_user_form"] = _user_form_defaults(None)
    if "user_management_group_form" not in st.session_state:
        st.session_state["user_management_group_form"] = _group_form_defaults(None)
    if "user_management_selected_group_id" not in st.session_state:
        st.session_state["user_management_selected_group_id"] = None

    users_tab, groups_tab = st.tabs(["Users", "Groups"])

    with users_tab:
        create_left, create_right = st.columns([1.2, 1])
        with create_left:
            st.subheader("Create user")
            with st.form("apmatia_user_create_form"):
                username = st.text_input("Username", value="")
                password = st.text_input("Password", value="", type="password")
                submitted = st.form_submit_button("Create user")
            if submitted:
                try:
                    create_user(username=username, password=password)
                except ApiError as error:
                    st.error(f"Unable to create user: {error.detail}")
                else:
                    st.success("User created.")
                    st.rerun()
        with create_right:
            st.subheader("Current account")
            current_user = _current_user(users)
            if current_user is None:
                st.info("Your current account is not available in the user list.")
            else:
                defaults = _user_form_defaults(current_user)
                with st.form("apmatia_user_edit_form"):
                    username = st.text_input("Username", value=str(defaults["username"]))
                    password = st.text_input("Password", value="", type="password")
                    is_enabled = st.checkbox("Enabled", value=bool(defaults["is_enabled"]))
                    submitted = st.form_submit_button("Save account")
                if submitted:
                    payload: dict[str, object] = {
                        "username": username,
                        "is_enabled": is_enabled,
                    }
                    if password.strip():
                        payload["password"] = password
                    try:
                        update_user(int(current_user["id"]), **payload)
                    except ApiError as error:
                        st.error(f"Unable to save account: {error.detail}")
                    else:
                        st.success("Account updated.")
                        st.rerun()
                if st.button("Delete my account", key="delete_current_user", use_container_width=True):
                    try:
                        delete_user(int(current_user["id"]))
                    except ApiError as error:
                        st.error(f"Unable to delete account: {error.detail}")
                    else:
                        st.session_state["auth_token"] = None
                        st.session_state["authenticated_user"] = None
                        st.success("Account deleted.")
                        st.rerun()

        st.divider()
        st.subheader("All users")
        if not users:
            st.info("No users have been created yet.")
        else:
            for user in users:
                if not isinstance(user, dict):
                    continue
                with st.container(border=True):
                    st.write(f"**{user.get('username') or 'Unnamed user'}**")
                    st.caption(
                        "ID {id} · enabled {enabled}".format(
                            id=user.get("id"),
                            enabled="yes" if user.get("is_enabled", True) else "no",
                        )
                    )
                    if _safe_int(user.get("id")) == current_user_id:
                        st.caption("This is your active account.")

    with groups_tab:
        group_left, group_right = st.columns([1.2, 1])
        with group_left:
            st.subheader("Create group")
            editing_group_id = _safe_int(st.session_state["user_management_group_form"].get("id"))
            with st.form("apmatia_group_form"):
                defaults = st.session_state["user_management_group_form"]
                name = st.text_input("Group name", value=str(defaults["name"]))
                description = st.text_area("Description", value=str(defaults["description"]), height=120)
                submitted = st.form_submit_button("Save group")
            if submitted:
                payload = {"name": name, "description": description}
                try:
                    if editing_group_id is None:
                        create_group(**payload)
                    else:
                        update_group(editing_group_id, **payload)
                except ApiError as error:
                    st.error(f"Unable to save group: {error.detail}")
                else:
                    st.success("Group saved.")
                    st.session_state["user_management_group_form"] = _group_form_defaults(None)
                    st.session_state["user_management_selected_group_id"] = None
                    st.rerun()
        with group_right:
            st.subheader("Selected group")
            selected_group_id = _safe_int(st.session_state.get("user_management_selected_group_id"))
            selected_group = next(
                (
                    group
                    for group in groups
                    if isinstance(group, dict) and _safe_int(group.get("id")) == selected_group_id
                ),
                None,
            )
            if selected_group is None:
                st.info("Select a group below to inspect its members.")
            else:
                st.write(f"**{selected_group.get('name') or 'Unnamed group'}**")
                st.caption(
                    "ID {id} · owner user {owner}".format(
                        id=selected_group.get("id"),
                        owner=selected_group.get("created_by_user_id"),
                    )
                )
                st.write(selected_group.get("description") or "")
                if _group_is_owned_by_current_user(selected_group, current_user_id):
                    if st.button("Edit selected group", key=f"edit_group_{selected_group.get('id')}"):
                        st.session_state["user_management_group_form"] = _group_form_defaults(selected_group)
                        st.rerun()
                    if st.button("Delete selected group", key=f"delete_group_{selected_group.get('id')}"):
                        try:
                            delete_group(int(selected_group["id"]))
                        except ApiError as error:
                            st.error(f"Unable to delete group: {error.detail}")
                        else:
                            if _safe_int(st.session_state.get("user_management_selected_group_id")) == _safe_int(
                                selected_group.get("id")
                            ):
                                st.session_state["user_management_selected_group_id"] = None
                            st.success("Group deleted.")
                            st.rerun()

                try:
                    members = _list_group_members_safe(int(selected_group["id"]))
                except (TypeError, ValueError):
                    members = []

                st.caption("Members")
                if not members:
                    st.info("No members are listed for this group yet.")
                else:
                    for membership in members:
                        with st.container(border=True):
                            st.write(
                                "User {user_id} · role {role}".format(
                                    user_id=membership.get("user_id"),
                                    role=membership.get("role"),
                                )
                            )
                            st.caption(
                                "Membership ID {id} · enabled {enabled}".format(
                                    id=membership.get("id"),
                                    enabled="yes" if membership.get("is_enabled", True) else "no",
                                )
                            )
                            if _group_is_owned_by_current_user(selected_group, current_user_id):
                                toggle_label = "Disable" if membership.get("is_enabled", True) else "Enable"
                                if membership.get("role") != "owner":
                                    if st.button(
                                        toggle_label,
                                        key=f"toggle_membership_{membership.get('id')}",
                                        use_container_width=True,
                                    ):
                                        try:
                                            set_group_membership_enabled(
                                                int(selected_group["id"]),
                                                int(membership["id"]),
                                                enabled=not bool(membership.get("is_enabled", True)),
                                            )
                                        except ApiError as error:
                                            st.error(f"Unable to update membership: {error.detail}")
                                        else:
                                            st.success("Membership updated.")
                                            st.rerun()

                if _group_is_owned_by_current_user(selected_group, current_user_id) and users:
                    st.divider()
                    with st.form(f"apmatia_group_add_member_form_{selected_group.get('id')}"):
                        member_user_options = [user.get("id") for user in users if user.get("id") is not None]
                        member_user_labels = {
                            _safe_int(user.get("id")): _user_label(user)
                            for user in users
                            if user.get("id") is not None
                        }
                        chosen_user_id = st.selectbox(
                            "User",
                            options=member_user_options,
                            index=0 if member_user_options else 0,
                            format_func=lambda value: member_user_labels.get(_safe_int(value), f"User {value}"),
                        )
                        role = st.selectbox("Role", options=["member", "owner"], index=0)
                        submitted = st.form_submit_button("Add member")
                    if submitted:
                        try:
                            add_group_member(
                                int(selected_group["id"]),
                                user_id=int(chosen_user_id),
                                role=role,
                            )
                        except ApiError as error:
                            st.error(f"Unable to add member: {error.detail}")
                        else:
                            st.success("Member added.")
                            st.rerun()

        st.divider()
        st.subheader("All groups")
        if not groups:
            st.info("No groups have been created yet.")
        else:
            for group in groups:
                if not isinstance(group, dict):
                    continue
                with st.container(border=True):
                    st.write(f"**{group.get('name') or 'Unnamed group'}**")
                    st.caption(
                        "ID {id} · owner user {owner}".format(
                            id=group.get("id"),
                            owner=group.get("created_by_user_id"),
                        )
                    )
                    description = str(group.get("description") or "").strip()
                    if description:
                        st.write(description)
                    if st.button("Open", key=f"open_group_{group.get('id')}", use_container_width=True):
                        st.session_state["user_management_selected_group_id"] = group.get("id")
                        st.rerun()
