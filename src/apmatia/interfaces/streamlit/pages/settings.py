"""Settings page for configuring Apmatia through the API."""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st

from apmatia.api.http.routes.settings_routes import SettingsPayload
from apmatia.interfaces.streamlit.components.filesystem_tree import render_filesystem_tree
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

        st.subheader("Agent Roots")
        roots_left, roots_right = st.columns(2)
        with roots_left:
            workspace_root = st.text_input(
                "Workspace root",
                value=current.get("workspace_root", ""),
                help="Base directory for agent workspace roots. Agent configs can point to subdirectories under this path.",
            )
        with roots_right:
            knowledge_root = st.text_input(
                "Knowledge root",
                value=current.get("knowledge_root", ""),
                help="Base directory for shared knowledge roots. Agents can point at shared or per-agent subdirectories here.",
            )
        st.caption(
            "Default roots are `~/.apmatia/workspace` and `~/.apmatia/knowledge`. "
            "Missing directories are created when settings are saved."
        )
        st.caption("Use the browser below to inspect the current contents of each root without guessing the path.")
        with st.expander("Browse current roots", expanded=False):
            browser_left, browser_right = st.columns(2)
            with browser_left:
                render_filesystem_tree(Path(workspace_root).expanduser(), label="Workspace browser", max_depth=2)
            with browser_right:
                render_filesystem_tree(Path(knowledge_root).expanduser(), label="Knowledge browser", max_depth=2)

        st.subheader("Time Zone")
        timezone = st.selectbox(
            "Alarm time zone",
            options=[
                "America/Phoenix",
                "America/Denver",
                "America/Chicago",
                "America/New_York",
                "UTC",
            ],
            index=_timezone_index(current.get("timezone", "America/Phoenix")),
            help="Alarms use this zone when combining the selected date and time. America/Phoenix ignores daylight saving time.",
        )
        clock_left, clock_right = st.columns(2)
        current_time_text = _format_time_clock(timezone)
        utc_time_text = datetime.now(dt_timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with clock_left:
            st.metric("Current local time", current_time_text)
        with clock_right:
            st.metric("Current UTC", utc_time_text)
        st.caption("Arizona option: `America/Phoenix` stays on standard time year-round and does not observe DST.")

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

        st.subheader("Terminal")
        terminal_left, terminal_right = st.columns(2)
        with terminal_left:
            terminal_background_color = st.color_picker(
                "Terminal background",
                value=str(current.get("terminal_background_color", "#000000") or "#000000"),
            )
            terminal_text_color = st.color_picker(
                "Terminal text",
                value=str(current.get("terminal_text_color", "#9dffad") or "#9dffad"),
            )
        with terminal_right:
            terminal_border_color = st.text_input(
                "Terminal border",
                value=str(current.get("terminal_border_color", "rgba(110, 255, 170, 0.35)") or "rgba(110, 255, 170, 0.35)"),
                help="Any valid CSS color is accepted.",
            )
            terminal_muted_color = st.text_input(
                "Terminal muted text",
                value=str(current.get("terminal_muted_color", "rgba(157, 255, 173, 0.72)") or "rgba(157, 255, 173, 0.72)"),
                help="Used for subtitles and helper text inside terminal panes.",
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
        workspace_root=workspace_root,
        knowledge_root=knowledge_root,
        timezone=timezone,
        theme=theme,
        font_family=font_family,
        accent_color=accent_color,
        font_size=int(font_size),
        title_bar_height=int(title_bar_height),
        title_bar_font_size=int(title_bar_font_size),
        terminal_background_color=terminal_background_color,
        terminal_text_color=terminal_text_color,
        terminal_border_color=terminal_border_color,
        terminal_muted_color=terminal_muted_color,
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
    st.session_state["ui_timezone"] = timezone
    st.session_state["ui_terminal_background_color"] = terminal_background_color
    st.session_state["ui_terminal_text_color"] = terminal_text_color
    st.session_state["ui_terminal_border_color"] = terminal_border_color
    st.session_state["ui_terminal_muted_color"] = terminal_muted_color
    st.session_state["settings_save_message"] = "Settings saved."
    st.rerun()


def _timezone_index(timezone_name: object) -> int:
    options = ["America/Phoenix", "America/Denver", "America/Chicago", "America/New_York", "UTC"]
    value = str(timezone_name or "").strip()
    if value in options:
        return options.index(value)
    return 0


def _format_time_clock(timezone_name: str) -> str:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = dt_timezone.utc
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
