"""Settings page for configuring Apmatia through the API."""
from __future__ import annotations

import streamlit as st

from src.api.http.routes.settings_routes import SettingsPayload
from src.interfaces.streamlit.api_client import ApiError, get_settings, save_settings


def render() -> None:
    """Render the settings page."""
    try:
        current = get_settings()
    except ApiError as error:
        st.error(f"Unable to load settings: {error.detail}")
        return

    st.title("Settings")
    st.caption("Configure Apmatia through the local API. Changes stay on this machine.")

    with st.form("apmatia_settings_form"):
        st.subheader("Runtime")
        llama_server_log_dir = st.text_input(
            "llama.cpp log directory",
            value=current.get("llama_server_log_dir", ""),
            help="Directory containing the llama.cpp server log files. Leave blank to use an environment override.",
        )

        st.subheader("Appearance")
        appearance_left, appearance_right = st.columns(2)
        with appearance_left:
            theme = st.selectbox(
                "Theme",
                options=["dark", "light", "system"],
                index=["dark", "light", "system"].index(current.get("theme", "dark")),
            )
            font_family = st.text_input(
                "Font family",
                value=current.get("font_family", "system-ui"),
            )
            accent_color = st.color_picker(
                "Accent color",
                value=str(current.get("accent_color", "#ff6b6b") or "#ff6b6b"),
            )
        with appearance_right:
            font_size = st.slider(
                "Font size",
                min_value=12,
                max_value=24,
                value=int(current.get("font_size", 16)),
            )
            title_bar_height = st.slider(
                "Title bar height",
                min_value=40,
                max_value=96,
                value=int(current.get("title_bar_height", 56)),
            )
            title_bar_font_size = st.slider(
                "Title bar font size",
                min_value=12,
                max_value=40,
                value=int(current.get("title_bar_font_size", 20)),
            )

        submitted = st.form_submit_button("Save settings")

    if not submitted:
        return

    payload = SettingsPayload(
        llama_server_log_dir=llama_server_log_dir,
        theme=theme,
        font_family=font_family,
        accent_color=accent_color,
        font_size=int(font_size),
        title_bar_height=int(title_bar_height),
        title_bar_font_size=int(title_bar_font_size),
    )

    try:
        save_settings(payload)
    except ApiError as error:
        st.error(f"Unable to save settings: {error.detail}")
        return

    st.session_state["ui_theme_preference"] = theme
    st.session_state["ui_font_family"] = font_family
    st.session_state["ui_accent_color"] = accent_color
    st.success("Settings saved.")
    st.rerun()
