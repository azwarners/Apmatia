"""Login page for user authentication."""
import streamlit as st

from src.interfaces.streamlit.api_client import ApiError, get_auth_session, login, register


def _hydrate_authenticated_session() -> None:
    session = get_auth_session()
    if session.get("authenticated"):
        st.session_state["auth_token"] = "api-session"
        st.session_state["authenticated_user"] = session
    else:
        st.session_state["auth_token"] = None
        st.session_state["authenticated_user"] = None


def show_auth_form():
    """Display sign-in and sign-up forms for user authentication."""
    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = None
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None

    try:
        session = get_auth_session()
    except ApiError as error:
        st.error(f"Unable to contact the API: {error.detail}")
        return False

    if session.get("authenticated"):
        st.session_state["auth_token"] = "api-session"
        st.session_state["authenticated_user"] = session
        return True

    tab1, tab2 = st.tabs(["Sign In", "Create Account"])

    with tab1:
        st.header("Sign In")
        with st.form("apmatia_signin_form"):
            sign_in_username = st.text_input("Username", key="signin_username")
            sign_in_password = st.text_input(
                "Password",
                key="signin_password",
                type="password",
            )
            sign_in_submitted = st.form_submit_button("Sign In")

        if sign_in_submitted:
            if not sign_in_username or not sign_in_password:
                st.warning("Please enter both username and password.")
            else:
                try:
                    response = login(sign_in_username, sign_in_password)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    _hydrate_authenticated_session()
                    st.success(f"Welcome back, {response.get('username', sign_in_username)}!")
                    st.rerun()

    with tab2:
        st.header("Create Account")
        with st.form("apmatia_signup_form"):
            sign_up_username = st.text_input("Username", key="signup_username")
            sign_up_password = st.text_input(
                "Password",
                key="signup_password",
                type="password",
            )
            sign_up_confirm = st.text_input(
                "Confirm Password",
                key="signup_confirm",
                type="password",
            )
            sign_up_submitted = st.form_submit_button("Create Account")

        if sign_up_submitted:
            if not sign_up_username or not sign_up_password:
                st.warning("Please enter both username and password.")
            elif sign_up_password != sign_up_confirm:
                st.warning("Passwords do not match.")
            else:
                try:
                    response = register(sign_up_username, sign_up_password)
                except ApiError as error:
                    st.error(error.detail)
                else:
                    user = response.get("user", {})
                    username = user.get("username", sign_up_username)
                    _hydrate_authenticated_session()
                    st.success(f"Account created for {username}! You are now signed in.")
                    st.rerun()

    return False


def render():
    """Render the login page."""
    return show_auth_form()
