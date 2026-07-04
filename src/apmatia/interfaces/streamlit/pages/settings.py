"""Settings page for configuring Apmatia through the API."""
from __future__ import annotations

import streamlit as st

from apmatia.api.http.routes.settings_routes import SettingsPayload
from apmatia.interfaces.streamlit.api_client import ApiError, get_settings, save_settings


def render() -> None:
    """Render the settings page."""
    try:
        current = get_settings()
    except ApiError as error:
        st.error(f"Unable to load settings: {error.detail}")
        return

    st.title("Settings")
    st.caption("Configure Apmatia through the local API. Changes stay on this machine.")

    saved_message = st.session_state.pop("settings_save_message", None)
    if saved_message:
        st.success(saved_message)

    with st.form("apmatia_settings_form"):
        st.subheader("Runtime")
        runtime_left, runtime_right = st.columns(2)
        with runtime_left:
            llama_server_log_dir = st.text_input(
                "llama.cpp log directory",
                value=current.get("llama_server_log_dir", ""),
                help="Directory containing the llama.cpp server log files. Leave blank to use an environment override.",
            )
            llama_server_executable_path = st.text_input(
                "llama-server executable",
                value=current.get("llama_server_executable_path", "llama-server"),
                help="Path to the local llama-server binary used for execution.",
            )
        with runtime_right:
            llama_server_default_args = st.text_area(
                "llama-server default args",
                value=str(current.get("llama_server_default_args", "")),
                height=120,
                help="One argument per line. These are passed to every local launch.",
            )

        st.subheader("Model Discovery")
        discovery_left, discovery_right = st.columns(2)
        with discovery_left:
            gguf_directories = st.text_area(
                "GGUF model libraries",
                value=current.get("gguf_directories", current.get("gguf_directory", "")),
                height=140,
                help="Use one directory per line or separate them with commas. The scanner will recurse through subdirectories in each library.",
            )
            st.caption("Example: `/home/nick/ServerData/models/llm` or `/home/nick/ServerData/models/llm, /home/nick/ServerData/models/vision`.")
            auto_scan_gguf_directory = st.checkbox(
                "Auto-scan GGUF directory on save",
                value=bool(current.get("auto_scan_gguf_directory", True)),
                help="Stored as a preference for future automation. GGUF directories are rescanned immediately when saved.",
            )
        with discovery_right:
            st.info(
                "The scanner records every GGUF file it finds recursively. "
                "At launch time, the executor will use the first GGUF file in a model directory."
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
        gguf_directories=gguf_directories,
        auto_scan_gguf_directory=auto_scan_gguf_directory,
        llama_server_executable_path=llama_server_executable_path,
        llama_server_default_args=llama_server_default_args,
        theme=theme,
        font_family=font_family,
        accent_color=accent_color,
        font_size=int(font_size),
        title_bar_height=int(title_bar_height),
        title_bar_font_size=int(title_bar_font_size),
    )

    try:
        with st.spinner("Saving settings..."):
            save_settings(payload)
    except ApiError as error:
        st.error(f"Unable to save settings: {error.detail}")
        return

    st.session_state["ui_theme_preference"] = theme
    st.session_state["ui_font_family"] = font_family
    st.session_state["ui_accent_color"] = accent_color
    st.session_state["settings_save_message"] = "Settings saved."
    st.rerun()
