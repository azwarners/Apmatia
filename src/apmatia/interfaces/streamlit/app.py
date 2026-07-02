"""Entry point for the Apmatia Streamlit interface."""
from pathlib import Path

import streamlit as st

from apmatia.api.internal.apmatia_ipe import ensure_ipe_coach_agent_for_user
from apmatia.interfaces.streamlit.api_client import ApiError, get_auth_session, get_settings, list_modules as list_module_catalog, logout
from apmatia.interfaces.streamlit.pages.login import show_auth_form
from apmatia.interfaces.streamlit.pages import (
    settings,
    model_management,
    module_management,
    agent_management,
    memory_management,
    module_views,
    tool_management,
    user_management,
    discussion,
    tutor,
    tutor_live_discussion,
    tutor_session_config,
    tutor_session_wiki,
)

FAVICON_PATH = Path(__file__).resolve().parents[4] / "assets" / "favicon.png"
PAGE_OPTIONS = [
    "discussion",
    "tutor",
    "tutor_session_config",
    "tutor_live_discussion",
    "tutor_session_wiki",
    "model_management",
    "module_management",
    "agent_management",
    "module_view",
    "user_management",
    "memory_management",
    "tool_management",
    "settings",
]
THEME_OPTIONS = ["dark", "light", "system"]


def _format_page_label(page: str) -> str:
    if page == "discussion":
        return "💬 Discussion"
    if page == "tutor":
        return "📚 Tutor"
    if page == "tutor_session_config":
        return "📚 Tutor · Session Config"
    if page == "tutor_live_discussion":
        return "📚 Tutor · Live Discussion"
    if page == "tutor_session_wiki":
        return "📚 Tutor · Session Wiki"
    if page == "model_management":
        return "🧩 AI Models"
    if page == "module_management":
        return "📦 Modules"
    if page == "agent_management":
        return "🤖 Agents"
    if page == "user_management":
        return "👥 Users & Groups"
    if page == "tool_management":
        return "🛠️ Tools"
    if page == "memory_management":
        return "🧠 Memories"
    if page == "settings":
        return "⚙️ Settings"
    return page.title()


def require_auth():
    """Check if user is authenticated, redirect to login if not."""
    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = None
    if "authenticated_user" not in st.session_state:
        st.session_state["authenticated_user"] = None

    try:
        session = get_auth_session()
    except ApiError as error:
        st.error(f"Unable to contact the API: {error.detail}")
        return False

    if not session.get("authenticated"):
        st.session_state["auth_token"] = None
        st.session_state["authenticated_user"] = None
        return False

    st.session_state["auth_token"] = "api-session"
    st.session_state["authenticated_user"] = session
    return True


def initialize_ui_preferences():
    """Load persisted UI preferences once per session."""
    if "ui_theme_preference" in st.session_state and "ui_font_family" in st.session_state:
        return

    try:
        current_settings = get_settings()
    except ApiError:
        st.session_state["ui_theme_preference"] = "dark"
        st.session_state.setdefault("ui_font_family", "system-ui")
        return

    preference = str(current_settings.get("theme", "dark") or "dark").lower()
    if preference not in THEME_OPTIONS:
        preference = "dark"
    st.session_state["ui_theme_preference"] = preference
    st.session_state["ui_font_family"] = str(current_settings.get("font_family", "system-ui") or "system-ui")


def apply_theme_styles():
    """Apply the active appearance theme."""
    theme = st.session_state.get("ui_theme_preference", "dark")
    font_family = st.session_state.get("ui_font_family", "system-ui")
    css = """
<style>
:root {
  --apm-bg: #0e1117;
  --apm-surface: #171b24;
  --apm-sidebar: #202531;
  --apm-border: rgba(255, 255, 255, 0.10);
  --apm-text: #f5f7fb;
  --apm-muted: #b8c0d4;
  --apm-accent: #ff6b6b;
  --apm-font-family: %s;
}

@media (prefers-color-scheme: light) {
  :root {
    --apm-bg: #f6f7fb;
    --apm-surface: #ffffff;
    --apm-sidebar: #eef1f7;
    --apm-border: rgba(15, 23, 42, 0.10);
    --apm-text: #18212f;
    --apm-muted: #516074;
    --apm-accent: #dd4b39;
  }
}
"""
    font_family_css = ", ".join(
        f'"{part.strip()}"' if " " in part.strip() and not part.strip().startswith("var(") else part.strip()
        for part in [font_family]
    )
    css = css % font_family_css
    if theme == "dark":
        css += """
:root {
  --apm-bg: #0e1117;
  --apm-surface: #171b24;
  --apm-sidebar: #202531;
  --apm-border: rgba(255, 255, 255, 0.10);
  --apm-text: #f5f7fb;
  --apm-muted: #b8c0d4;
  --apm-accent: #ff6b6b;
}
"""
    elif theme == "light":
        css += """
:root {
  --apm-bg: #f6f7fb;
  --apm-surface: #ffffff;
  --apm-sidebar: #eef1f7;
  --apm-border: rgba(15, 23, 42, 0.10);
  --apm-text: #18212f;
  --apm-muted: #516074;
  --apm-accent: #dd4b39;
}
"""
    css += """
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stHeader"] {
  background: var(--apm-bg);
}

html,
body {
  overflow-x: hidden;
}

[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
  overflow-x: hidden;
}

[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .block-container,
[data-testid="stAppViewContainer"] [data-testid="stHorizontalBlock"],
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"],
[data-testid="stAppViewContainer"] [data-testid="column"],
[data-testid="stAppViewContainer"] [data-testid="column"] > div {
  min-width: 0 !important;
  max-width: 100% !important;
}

[data-testid="stHeader"] {
  pointer-events: none;
  z-index: 2147483645;
}

[data-testid="stHeader"] [data-testid="stToolbar"] {
  pointer-events: none !important;
}

[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] * {
  pointer-events: auto !important;
  cursor: pointer !important;
}

[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] {
  position: relative;
  z-index: 2147483646;
  min-width: 2.75rem;
  min-height: 2.75rem;
}

[data-testid="stAppViewContainer"] > .main .block-container {
  padding-top: 0.15rem;
  padding-right: 0.85rem;
  padding-left: 0.85rem;
  box-sizing: border-box;
  width: 100%;
  max-width: 72rem;
  margin-left: auto;
  margin-right: auto;
}

[data-testid="stSidebar"] {
  background: var(--apm-sidebar);
  border-right: 1px solid var(--apm-border);
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
  opacity: 1 !important;
  visibility: visible !important;
  pointer-events: auto !important;
  z-index: 2147483646;
}

[data-testid="stSidebarCollapseButton"] button {
  min-width: 2.75rem;
  min-height: 2.75rem;
}

@media (max-width: 767.98px) {
  [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] {
    position: fixed !important;
    top: max(0.35rem, env(safe-area-inset-top));
    left: max(0.35rem, env(safe-area-inset-left));
    transform: none !important;
  }
}

[data-testid="stSidebar"] *,
[data-testid="stAppViewContainer"] * {
  color: var(--apm-text);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p {
  color: var(--apm-text);
}

.stButton > button,
[data-baseweb="button"] {
  border-radius: 10px;
  white-space: nowrap;
}

.apm-menu-panel {
  border: 1px solid var(--apm-border);
  border-radius: 16px;
  background: var(--apm-surface);
  padding: 1rem 1rem 1.1rem;
  margin-top: 0.35rem;
}

.apm-menu-panel [data-testid="stButton"] button,
.apm-menu-panel [data-baseweb="button"] {
  min-height: 2.75rem;
}

.apm-menu-panel [data-testid="stMarkdownContainer"] p {
  white-space: nowrap;
}

.apm-menu-panel hr {
  margin: 0.9rem 0;
}

.apm-header-menu {
  position: fixed;
  top: 0.35rem;
  right: 1rem;
  z-index: 2147483647;
}

div[data-testid="stPopover"] {
  position: fixed !important;
  top: 0.35rem !important;
  right: 1rem !important;
  width: 2.4rem !important;
  min-width: 2.4rem !important;
  max-width: 2.4rem !important;
  z-index: 2147483647 !important;
}

div[data-testid="stPopover"] > div,
div[data-testid="stPopover"] button {
  width: 2.4rem !important;
  min-width: 2.4rem !important;
  max-width: 2.4rem !important;
}

div[data-testid="stPopover"] button {
  min-height: 2.4rem !important;
  padding: 0 !important;
  border: none !important;
  background: transparent !important;
  color: var(--apm-text) !important;
  font-size: 1.55rem !important;
  line-height: 1 !important;
  box-shadow: none !important;
}

.apm-header-menu button,
div[data-testid="stPopover"] button {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  position: relative;
  z-index: 2;
  cursor: pointer;
  color: var(--apm-text) !important;
  font-size: 1.55rem;
  line-height: 1;
  padding: 0;
  margin: 0;
  background: transparent;
  border: none;
  user-select: none;
  text-align: right;
  text-decoration: none;
  opacity: 1;
  min-width: 2.4rem;
  min-height: 2.4rem;
}

div[data-testid="stPopover"] button svg,
div[data-testid="stPopover"] button [data-testid="stIconMaterial"],
.apm-header-menu button svg,
.apm-header-menu button [data-testid="stIconMaterial"] {
  display: none !important;
}

div[data-testid="stPopover"] button::after,
.apm-header-menu button::after {
  content: none !important;
}

.apm-header-menu-trigger {
  display: inline-grid;
  gap: 0.18rem;
  justify-items: center;
  align-content: center;
  width: 0.55rem;
  height: 1.15rem;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  opacity: 1 !important;
}

.apm-header-menu-trigger-dot {
  display: block;
  width: 0.24rem;
  height: 0.24rem;
  border-radius: 999px;
  background: var(--apm-text);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.18);
}

.apm-header-menu-panel {
  position: fixed;
  top: 3.75rem;
  right: 1rem;
  left: auto;
  width: 264px;
  z-index: 1;
  border: 1px solid var(--apm-border);
  border-radius: 16px;
  background: var(--apm-surface);
  padding: 1rem;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
  overflow: visible;
  margin: 0;
}

.apm-header-menu-panel p {
  margin: 0;
  color: var(--apm-muted);
}

.apm-header-menu-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 1rem;
}

.apm-header-menu-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0 0.8rem;
  border: 1px solid var(--apm-border);
  border-radius: 12px;
  color: var(--apm-text) !important;
  text-decoration: none !important;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.02);
  font-weight: 500;
  box-shadow: none;
}

.apm-header-menu-link.is-active {
  border-color: rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.07);
}

.apm-header-menu-link *,
.apm-header-menu-link span {
  color: inherit !important;
  text-decoration: none !important;
}

.apm-header-menu-link:visited,
.apm-header-menu-link:hover,
.apm-header-menu-link:focus,
.apm-header-menu-link:active {
  color: var(--apm-text) !important;
  text-decoration: none !important;
}

.apm-header-menu-divider {
  height: 1px;
  margin: 1rem 0;
  background: var(--apm-border);
}

.apm-header-menu-logout {
  width: 100%;
}

.apm-header-menu-settings {
  width: 100%;
}

hr {
  border-color: var(--apm-border);
}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar navigation."""
    st.sidebar.title("Apmatia")
    if "selected_page" not in st.session_state or st.session_state["selected_page"] not in PAGE_OPTIONS:
        st.session_state["selected_page"] = "discussion"
    tutor_active = st.session_state["selected_page"] in {
        "tutor",
        "tutor_session_config",
        "tutor_live_discussion",
        "tutor_session_wiki",
    }
    visible_modules = _visible_module_catalog()

    def _nav_button(page: str) -> None:
        if st.sidebar.button(
            _format_page_label(page),
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if st.session_state["selected_page"] == page else "secondary",
        ):
            st.session_state["selected_page"] = page
            st.rerun()

    _nav_button("discussion")
    _nav_button("tutor")
    if tutor_active:
        st.sidebar.subheader("Tutor")
        _nav_button("tutor_session_config")
        _nav_button("tutor_live_discussion")
        _nav_button("tutor_session_wiki")
    if visible_modules:
        st.sidebar.divider()
        st.sidebar.subheader("Modules")
        for module in visible_modules:
            _render_module_sidebar_section(module)
    st.sidebar.divider()
    st.sidebar.subheader("Management")
    _nav_button("model_management")
    _nav_button("module_management")
    _nav_button("agent_management")
    _nav_button("user_management")
    _nav_button("memory_management")
    _nav_button("tool_management")
    st.sidebar.divider()
    _nav_button("settings")
    return st.session_state["selected_page"]


def _visible_module_catalog() -> list[dict[str, object]]:
    try:
        modules = list_module_catalog()
    except ApiError:
        return []

    visible_modules: list[dict[str, object]] = []
    for module in modules:
        if bool(module.get("hidden", False)):
            continue
        visible_views = [
            view
            for view in list(module.get("views") or [])
            if not bool(view.get("effective_hidden", False))
        ]
        visible_modules.append({**module, "views": visible_views})
    return visible_modules


def _render_module_sidebar_section(module: dict[str, object]) -> None:
    module_id = str(module.get("module_id") or "")
    module_name = str(module.get("name") or module_id or "Unnamed module")
    module_views = list(module.get("views") or [])
    is_active_module = (
        st.session_state.get("selected_page") == "module_view"
        and st.session_state.get("selected_module_id") == module_id
    )

    if st.sidebar.button(
        module_name,
        key=f"nav_module_{module_id}",
        use_container_width=True,
        type="primary" if is_active_module else "secondary",
    ):
        _select_module_for_navigation(module_id, module_views)

    if not is_active_module:
        return

    st.sidebar.subheader(module_name)
    for view in module_views:
        view_id = str(view.get("view_id") or "")
        view_name = str(view.get("name") or view_id or "Unnamed view")
        is_active_view = st.session_state.get("selected_module_view_id") == view_id
        if st.sidebar.button(
            view_name,
            key=f"nav_module_view_{view_id}",
            use_container_width=True,
            type="primary" if is_active_view else "secondary",
        ):
            st.session_state["selected_page"] = "module_view"
            st.session_state["selected_module_id"] = module_id
            st.session_state["selected_module_view_id"] = view_id
            st.rerun()


def _select_module_for_navigation(module_id: str, module_views: list[dict[str, object]]) -> None:
    st.session_state["selected_page"] = "module_view"
    st.session_state["selected_module_id"] = module_id
    current_view_id = st.session_state.get("selected_module_view_id")
    visible_view_ids = {str(view.get("view_id") or "") for view in module_views}
    if current_view_id in visible_view_ids:
        st.session_state["selected_module_view_id"] = current_view_id
    else:
        st.session_state["selected_module_view_id"] = None if not module_views else str(module_views[0].get("view_id") or "")
    st.rerun()


def _set_theme_preference(theme: str) -> None:
    st.session_state["ui_theme_preference"] = theme
    st.rerun()


def _show_settings() -> None:
    st.session_state["selected_page"] = "settings"
    st.rerun()


def _clear_query_params() -> None:
    st.query_params.clear()


def _logout() -> None:
    try:
        logout()
    except ApiError as error:
        st.error(f"Unable to log out: {error.detail}")
    else:
        st.session_state["auth_token"] = None
        st.session_state["authenticated_user"] = None
        _clear_query_params()
        st.rerun()


def _process_header_actions() -> None:
    action = st.query_params.get("action")
    nav = st.query_params.get("nav")
    theme = st.query_params.get("theme")

    if nav == "settings":
        st.session_state["selected_page"] = "settings"
        _clear_query_params()
        st.rerun()

    if theme in THEME_OPTIONS:
        st.session_state["ui_theme_preference"] = theme
        _clear_query_params()
        st.rerun()

    if action == "logout":
        _logout()


def render_top_bar():
    """Render the authenticated session controls."""
    username = st.session_state["authenticated_user"]["username"]
    current_theme = st.session_state.get("ui_theme_preference", "dark")

    with st.popover("⋮", key="apm_header_menu", width=264):
        st.caption("Appearance")
        theme_columns = st.columns(3)
        for column, (label, value) in zip(
            theme_columns,
            (("Dark", "dark"), ("Light", "light"), ("System", "system")),
        ):
            with column:
                button_type = "primary" if current_theme == value else "secondary"
                if st.button(
                    label,
                    key=f"theme_{value}_button",
                    type=button_type,
                    use_container_width=True,
                ):
                    _set_theme_preference(value)

        st.divider()
        if st.button("⚙️ Settings", key="header_settings_button", use_container_width=True):
            _show_settings()

        st.divider()
        st.caption(f"Logged in as: {username}")
        st.divider()
        if st.button("Log Out", key="header_logout_button", use_container_width=True):
            _logout()


def main():
    st.set_page_config(page_title="Apmatia", page_icon=str(FAVICON_PATH), layout="centered")
    st.set_option("client.showSidebarNavigation", False)
    initialize_ui_preferences()
    apply_theme_styles()

    # Show login if not authenticated.
    if not require_auth():
        show_auth_form()
        return

    session_user = st.session_state.get("authenticated_user") or {}
    try:
        user_id = session_user.get("user_id")
        if user_id is not None:
            ensure_ipe_coach_agent_for_user(int(user_id), username=str(session_user.get("username") or ""))
    except Exception:
        # Onboarding should never block the UI.
        pass

    _process_header_actions()
    render_top_bar()

    # Keep the custom sidebar visible while preserving top-menu navigation state.
    selected_page = render_sidebar()

    if selected_page == "settings":
        settings.render()
        return

    if selected_page == "model_management":
        model_management.render()
        return

    if selected_page == "module_management":
        module_management.render()
        return

    if selected_page == "agent_management":
        agent_management.render()
        return

    if selected_page == "module_view":
        module_views.render()
        return

    if selected_page == "user_management":
        user_management.render()
        return

    if selected_page == "tool_management":
        tool_management.render()
        return

    if selected_page == "memory_management":
        memory_management.render()
        return

    if selected_page == "discussion":
        discussion.render()
        return

    if selected_page == "tutor_session_config":
        tutor_session_config.render()
        return

    if selected_page == "tutor_live_discussion":
        tutor_live_discussion.render()
        return

    if selected_page == "tutor_session_wiki":
        tutor_session_wiki.render()
        return

    if selected_page == "tutor":
        tutor.render()


if __name__ == "__main__":
    main()
