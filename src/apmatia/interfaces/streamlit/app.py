"""Entry point for the Apmatia Streamlit interface."""
from pathlib import Path

import streamlit as st

from apmatia.api.internal.ipe import ensure_ipe_coach_agent_for_user
from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_discussion,
    discussion_state,
    get_auth_session,
    get_settings,
    list_agents,
    list_groups,
    list_group_members,
    list_module_view_items,
    list_modules as list_module_catalog,
    logout,
    open_discussion,
    discussion_tree,
)
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.renderers import render_navigation_pane
from apmatia.interfaces.streamlit.page_runtime import sync_page_generation
from apmatia.interfaces.streamlit.module_views.auth import show_auth_form
from apmatia.interfaces.streamlit.pages.archive import discussion
from apmatia.interfaces.streamlit.pages import module_views
from apmatia.lib.persistence.logger import get_logger

FAVICON_PATH = Path(__file__).resolve().parents[4] / "assets" / "favicon.png"
PAGE_OPTIONS = [
    "discussion",
    "module_view",
]
THEME_OPTIONS = ["dark", "light", "system"]
LOGGER = get_logger(__name__)


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
    if (
        "ui_theme_preference" in st.session_state
        and "ui_font_family" in st.session_state
        and "ui_terminal_background_color" in st.session_state
        and "ui_terminal_text_color" in st.session_state
        and "ui_terminal_border_color" in st.session_state
        and "ui_terminal_muted_color" in st.session_state
    ):
        return

    try:
        current_settings = get_settings()
    except ApiError:
        st.session_state["ui_theme_preference"] = "dark"
        st.session_state.setdefault("ui_font_family", "system-ui")
        st.session_state.setdefault("ui_terminal_background_color", "#000000")
        st.session_state.setdefault("ui_terminal_text_color", "#9dffad")
        st.session_state.setdefault("ui_terminal_border_color", "rgba(110, 255, 170, 0.35)")
        st.session_state.setdefault("ui_terminal_muted_color", "rgba(157, 255, 173, 0.72)")
        return

    preference = str(current_settings.get("theme", "dark") or "dark").lower()
    if preference not in THEME_OPTIONS:
        preference = "dark"
    st.session_state["ui_theme_preference"] = preference
    st.session_state["ui_font_family"] = str(current_settings.get("font_family", "system-ui") or "system-ui")
    st.session_state["ui_terminal_background_color"] = str(
        current_settings.get("terminal_background_color", "#000000") or "#000000"
    )
    st.session_state["ui_terminal_text_color"] = str(current_settings.get("terminal_text_color", "#9dffad") or "#9dffad")
    st.session_state["ui_terminal_border_color"] = str(
        current_settings.get("terminal_border_color", "rgba(110, 255, 170, 0.35)")
        or "rgba(110, 255, 170, 0.35)"
    )
    st.session_state["ui_terminal_muted_color"] = str(
        current_settings.get("terminal_muted_color", "rgba(157, 255, 173, 0.72)")
        or "rgba(157, 255, 173, 0.72)"
    )


def apply_theme_styles():
    """Apply the active appearance theme."""
    theme = st.session_state.get("ui_theme_preference", "dark")
    font_family = st.session_state.get("ui_font_family", "system-ui")
    terminal_background_color = st.session_state.get("ui_terminal_background_color", "#000000")
    terminal_text_color = st.session_state.get("ui_terminal_text_color", "#9dffad")
    terminal_border_color = st.session_state.get("ui_terminal_border_color", "rgba(110, 255, 170, 0.35)")
    terminal_muted_color = st.session_state.get("ui_terminal_muted_color", "rgba(157, 255, 173, 0.72)")
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
  --apm-terminal-bg: %s;
  --apm-terminal-text: %s;
  --apm-terminal-border: %s;
  --apm-terminal-muted: %s;
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
    css = css % (
        font_family_css,
        terminal_background_color,
        terminal_text_color,
        terminal_border_color,
        terminal_muted_color,
    )
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
    visible_modules = _visible_module_catalog()
    if "selected_page" not in st.session_state or st.session_state["selected_page"] not in PAGE_OPTIONS:
        st.session_state["selected_page"] = "module_view"
        if visible_modules:
            first_module = visible_modules[0]
            st.session_state["selected_module_id"] = str(first_module.get("module_id") or "")
            first_views = list(first_module.get("views") or [])
            st.session_state["selected_module_view_id"] = (
                str(first_views[0].get("view_id") or "") if first_views else None
            )
    if _contacts_shell_active():
        return _render_contacts_sidebar()
    if _agent_loops_shell_active():
        return _render_agent_loops_sidebar()

    st.sidebar.title("Apmatia")

    if visible_modules:
        st.sidebar.divider()
        st.sidebar.subheader("Modules")
        for module in visible_modules:
            _render_module_sidebar_section(module)
    return st.session_state["selected_page"]


def _contacts_shell_active() -> bool:
    return bool(st.session_state.get("contacts_shell_active"))


def _agent_loops_shell_active() -> bool:
    return st.session_state.get("selected_page") == "module_view" and st.session_state.get("selected_module_id") == "agent_loops"


def _current_user_id() -> int | None:
    authenticated_user = st.session_state.get("authenticated_user")
    if not isinstance(authenticated_user, dict):
        return None
    try:
        user_id = authenticated_user.get("user_id")
        return None if user_id is None else int(user_id)
    except (TypeError, ValueError):
        return None


def _visible_agent(agent: dict[str, object], current_user_id: int | None, visible_group_ids: set[int]) -> bool:
    if current_user_id is None:
        return True
    try:
        owner_user_id = agent.get("owner_user_id")
        owner_group_id = agent.get("owner_group_id")
    except AttributeError:
        return False
    if owner_user_id == current_user_id:
        return True
    if owner_group_id is not None and owner_group_id in visible_group_ids:
        return True
    return False


def _render_contacts_sidebar():
    try:
        contacts = _contact_roster()
    except ApiError as error:
        st.sidebar.title("Contacts")
        st.sidebar.error(f"Unable to load contacts: {error.detail}")
        return st.session_state["selected_page"]

    if st.sidebar.button("Back to Apmatia", key="contacts_exit_top", use_container_width=True):
        _deactivate_contacts_shell()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.title("Contacts")

    active_contact_id = str(st.session_state.get("contacts_active_contact_id") or "")
    active_contact_type = str(st.session_state.get("contacts_active_contact_type") or "")
    contacts = _filter_contacts_for_active_group(
        contacts,
        active_contact_type=active_contact_type,
        active_contact_id=active_contact_id,
    )
    if active_contact_type == "group" and active_contact_id:
        st.sidebar.caption(f"Showing members of {str(st.session_state.get('contacts_active_contact_label') or 'this group')}.")

    current_speaker_contact_id = None
    try:
        snapshot = discussion_state()
    except ApiError:
        snapshot = None
    if isinstance(snapshot, dict):
        activity = snapshot.get("activity") if isinstance(snapshot.get("activity"), dict) else None
        speaker_name = str(activity.get("speaker_name") or "").strip().lower() if isinstance(activity, dict) else ""
        if speaker_name:
            for contact in contacts:
                if str(contact.get("contact_type") or "") != "agent":
                    continue
                if str(contact.get("label") or "").strip().lower() == speaker_name:
                    current_speaker_contact_id = str(contact.get("contact_id") or "")
                    break

    if contacts and (not active_contact_id or active_contact_id not in {str(contact.get("contact_id") or "") for contact in contacts}):
        _activate_contacts_contact(contacts[0])
        st.rerun()

    if not contacts:
        pass
    else:
        for contact in contacts:
            contact_id = str(contact.get("contact_id") or "")
            contact_label = str(contact.get("label") or contact_id or "Contact")
            button_type = (
                "primary"
                if (active_contact_id and contact_id == active_contact_id)
                or (current_speaker_contact_id and contact_id == current_speaker_contact_id)
                else "secondary"
            )
            if st.sidebar.button(
                contact_label,
                key=f"contacts_nav_{contact_id or contact_label}",
                type=button_type,
                use_container_width=True,
            ):
                _activate_contacts_contact(contact)
                st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("Back to Apmatia", key="contacts_exit_bottom", use_container_width=True):
        _deactivate_contacts_shell()
        st.rerun()

    return "discussion"


def _render_agent_loops_sidebar() -> str:
    if st.sidebar.button("Back to Apmatia", key="agent_loops_exit_top", use_container_width=True):
        _deactivate_agent_loops_shell()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.title("Agent Loops")

    try:
        modules = _visible_module_catalog()
    except ApiError as error:
        st.sidebar.error(f"Unable to load module views: {error.detail}")
        return st.session_state["selected_page"]

    module = next((item for item in modules if str(item.get("module_id") or "") == "agent_loops"), None)
    if module is None:
        st.sidebar.info("Agent Loops is not available yet.")
        return st.session_state["selected_page"]

    contacts_view = next(
        (
            view
            for view in list(module.get("views") or [])
            if str((view.get("metadata") or {}).get("object_type") or "").strip().lower() == "contact"
            and not bool(view.get("effective_hidden", False))
        ),
        None,
    )
    if contacts_view is None:
        st.sidebar.info("Agent Loops does not currently expose a contact list.")
        return st.session_state["selected_page"]

    contact_items = list_module_view_items(str(contacts_view.get("view_id") or ""))

    active_contact_id = str(st.session_state.get("agent_loops_selected_contact_id") or "")
    valid_contact_ids = {str(item.get("id") or "").strip() for item in contact_items if str(item.get("id") or "").strip()}
    if contact_items and (not active_contact_id or active_contact_id not in valid_contact_ids):
        _activate_agent_loops_contact(contact_items[0])
        st.rerun()

    st.session_state["agent_loops_shell_active"] = True
    st.session_state["agent_loops_shell_sidebar_rendered"] = True

    if contact_items:
        for contact in contact_items:
            contact_id = str(contact.get("id") or "")
            contact_label = str(contact.get("title") or contact.get("label") or contact_id or "Contact")
            button_type = "primary" if active_contact_id and contact_id == active_contact_id else "secondary"
            if st.sidebar.button(
                contact_label,
                key=f"agent_loops_nav_{contact_id or contact_label}",
                type=button_type,
                use_container_width=True,
            ):
                _activate_agent_loops_contact(contact)
                st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("Back to Apmatia", key="agent_loops_exit_bottom", use_container_width=True):
        _deactivate_agent_loops_shell()
        st.rerun()

    return "module_view"


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


def _contact_roster() -> list[dict[str, object]]:
    try:
        groups = list_groups()
    except ApiError:
        groups = []
    current_user_id = _current_user_id()
    visible_group_ids = {
        int(group.get("id"))
        for group in groups
        if isinstance(group, dict) and group.get("id") is not None
    }
    agents = [
        agent
        for agent in list_agents()
        if _visible_agent(agent, current_user_id, visible_group_ids)
    ]
    contacts: list[dict[str, object]] = []

    for agent in agents:
        agent_id = agent.get("id")
        if agent_id is None:
            continue
        agent_key = str(agent_id)
        contacts.append(
            {
                "contact_id": f"agent:{agent_key}",
                "contact_type": "agent",
                "label": str(agent.get("name") or f"Agent {agent_key}"),
                "discussion_id": None,
            }
        )

    for group in groups:
        group_id = group.get("id")
        if group_id is None:
            continue
        group_key = str(group_id)
        contacts.append(
            {
                "contact_id": f"group:{group_key}",
                "contact_type": "group",
                "label": str(group.get("name") or f"Group {group_key}"),
                "discussion_id": None,
            }
        )

    return sorted(
        contacts,
        key=lambda contact: str(contact.get("label") or "").lower(),
    )


def _group_member_agent_ids(group_id: int) -> set[int]:
    try:
        memberships = list_group_members(group_id)
    except ApiError:
        return set()

    member_ids: set[int] = set()
    for membership in memberships:
        if not isinstance(membership, dict):
            continue
        if not bool(membership.get("is_enabled", False)):
            continue
        if str(membership.get("member_kind") or "user").strip().lower() != "agent":
            continue
        try:
            agent_id = int(membership.get("agent_id"))
        except (TypeError, ValueError):
            continue
        member_ids.add(agent_id)
    return member_ids


def _filter_contacts_for_active_group(
    contacts: list[dict[str, object]],
    *,
    active_contact_type: str,
    active_contact_id: str,
) -> list[dict[str, object]]:
    if active_contact_type != "group":
        return contacts

    try:
        group_id = int(active_contact_id.split(":", 1)[1])
    except (IndexError, ValueError):
        return contacts

    member_agent_ids = _group_member_agent_ids(group_id)
    if not member_agent_ids:
        return [contact for contact in contacts if str(contact.get("contact_id") or "") == active_contact_id]

    filtered_contacts: list[dict[str, object]] = []
    for contact in contacts:
        contact_id = str(contact.get("contact_id") or "").strip()
        if contact_id == active_contact_id:
            filtered_contacts.append(contact)
            continue
        if str(contact.get("contact_type") or "") != "agent":
            continue
        agent_id = _contacts_agent_id(contact)
        if agent_id is not None and agent_id in member_agent_ids:
            filtered_contacts.append(contact)
    return filtered_contacts or contacts


def _activate_contacts_contact(contact: dict[str, object]) -> None:
    contact_id = str(contact.get("contact_id") or "").strip()
    if not contact_id:
        return
    st.session_state["contacts_shell_active"] = True
    st.session_state["contacts_active_contact_id"] = contact_id
    st.session_state["contacts_active_contact_label"] = str(contact.get("label") or contact_id)
    st.session_state["contacts_active_contact_type"] = str(contact.get("contact_type") or "")
    contact_type, raw_contact_id = contact_id.split(":", 1)
    try:
        numeric_contact_id = int(raw_contact_id)
    except ValueError:
        numeric_contact_id = None
    if contact_type == "agent" and numeric_contact_id is not None:
        st.session_state["contacts_active_agent_id"] = numeric_contact_id
    else:
        st.session_state["contacts_active_agent_id"] = None

    contact_discussion_ids = st.session_state.get("contacts_contact_discussion_ids")
    if not isinstance(contact_discussion_ids, dict):
        contact_discussion_ids = {}
        st.session_state["contacts_contact_discussion_ids"] = contact_discussion_ids

    discussion_id = str(contact_discussion_ids.get(contact_id) or "").strip() or None
    if discussion_id is None:
        discussion_id = _open_or_create_contact_discussion(
            contact_type=contact_type,
            contact_id=numeric_contact_id,
            label=str(contact.get("label") or contact_id),
        )
    if discussion_id:
        contact_discussion_ids[contact_id] = discussion_id
        st.session_state["contacts_contact_discussion_ids"] = contact_discussion_ids
        st.session_state["contacts_active_discussion_id"] = discussion_id


def _contacts_agent_id(contact: dict[str, object]) -> int | None:
    if str(contact.get("contact_type") or "") != "agent":
        return None
    contact_id = str(contact.get("contact_id") or "")
    if ":" not in contact_id:
        return None
    try:
        return int(contact_id.split(":", 1)[1])
    except ValueError:
        return None


def _discussion_matches_contact(
    discussion: dict[str, object],
    *,
    contact_type: str,
    contact_id: int,
) -> bool:
    if contact_type == "group":
        return int(discussion.get("group_id") or 0) == contact_id

    if contact_type != "agent":
        return False

    participant_agent_ids = discussion.get("participant_agent_ids") or []
    try:
        return contact_id in {int(candidate) for candidate in participant_agent_ids if candidate is not None}
    except (TypeError, ValueError):
        return False


def _find_existing_contact_discussion_id(*, contact_type: str, contact_id: int | None) -> str | None:
    if contact_id is None:
        return None

    try:
        tree = discussion_tree()
    except ApiError:
        return None

    discussions = tree.get("discussions")
    if not isinstance(discussions, list):
        return None

    matching_discussions = [
        discussion
        for discussion in discussions
        if isinstance(discussion, dict) and _discussion_matches_contact(
            discussion,
            contact_type=contact_type,
            contact_id=contact_id,
        )
    ]
    if not matching_discussions:
        return None

    def _discussion_sort_key(discussion: dict[str, object]) -> tuple[str, str]:
        return (
            str(discussion.get("updated_at") or ""),
            str(discussion.get("created_at") or ""),
        )

    matching_discussions.sort(key=_discussion_sort_key, reverse=True)
    return str(matching_discussions[0].get("discussion_id") or "").strip() or None


def _open_or_create_contact_discussion(*, contact_type: str, contact_id: int | None, label: str) -> str | None:
    if contact_id is None:
        return None

    existing_discussion_id = _find_existing_contact_discussion_id(
        contact_type=contact_type,
        contact_id=contact_id,
    )
    if existing_discussion_id is not None:
        try:
            open_discussion(existing_discussion_id)
        except ApiError:
            pass
        return existing_discussion_id

    create_payload: dict[str, object] = {"title": label, "chat_mode": "round_robin"}
    if contact_type == "agent":
        create_payload["agent_id"] = contact_id
        create_payload["participant_agent_ids"] = [contact_id]
    elif contact_type == "group":
        create_payload["group_id"] = contact_id
    else:
        return None

    try:
        created = create_discussion(**create_payload)
    except ApiError:
        return None
    discussion_id = str(created.get("discussion", {}).get("discussion_id") or "").strip() or None
    if discussion_id is not None:
        try:
            open_discussion(discussion_id)
        except ApiError:
            pass
    return discussion_id


def _deactivate_contacts_shell() -> None:
    for key in (
        "contacts_shell_active",
        "contacts_active_contact_id",
        "contacts_active_contact_label",
        "contacts_active_contact_type",
        "contacts_active_agent_id",
        "contacts_active_discussion_id",
    ):
        st.session_state.pop(key, None)


def _deactivate_agent_loops_shell() -> None:
    for key in (
        "agent_loops_shell_active",
        "agent_loops_shell_sidebar_rendered",
        "agent_loops_selected_contact_id",
        "selected_module_id",
        "selected_module_view_id",
    ):
        st.session_state.pop(key, None)
    st.session_state["selected_page"] = "module_view"
    st.session_state["selected_module_id"] = "module_manager"
    st.session_state["selected_module_view_id"] = "module_manager.module_manager.view"


def _activate_agent_loops_contact(contact: dict[str, object]) -> None:
    contact_id = str(contact.get("id") or "").strip()
    if not contact_id:
        return
    st.session_state["agent_loops_shell_active"] = True
    st.session_state["agent_loops_selected_contact_id"] = contact_id
    st.session_state["selected_module_id"] = "agent_loops"


def _render_module_sidebar_section(module: dict[str, object]) -> None:
    module_id = str(module.get("module_id") or "")
    module_name = _module_display_name(module)
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

    for view in module_views:
        view_id = str(view.get("view_id") or "")
        view_name = str(view.get("name") or view_id or "Unnamed view")
        if view_name == module_name:
            continue
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
    if module_id == "contacts_and_discussions":
        LOGGER.info(
            "Module navigation selected discussion shell",
            extra={
                "selected_page": "discussion",
                "selected_module_id": module_id,
                "selected_module_view_id": "contacts_and_discussions.chat_targets.view",
            },
        )
        st.session_state["selected_page"] = "discussion"
        st.session_state["selected_module_id"] = module_id
        st.session_state["selected_module_view_id"] = "contacts_and_discussions.chat_targets.view"
        st.session_state["contacts_shell_active"] = True
    elif module_id == "agent_loops":
        selected_module_view_id = None if not module_views else str(module_views[0].get("view_id") or "")
        LOGGER.info(
            "Module navigation selected module view shell",
            extra={
                "selected_page": "module_view",
                "selected_module_id": module_id,
                "selected_module_view_id": selected_module_view_id or "",
            },
        )
        st.session_state["selected_page"] = "module_view"
        st.session_state["selected_module_id"] = module_id
        st.session_state["selected_module_view_id"] = selected_module_view_id
        st.session_state["agent_loops_shell_active"] = True
    else:
        current_view_id = st.session_state.get("selected_module_view_id")
        visible_view_ids = {str(view.get("view_id") or "") for view in module_views}
        next_view_id = current_view_id if current_view_id in visible_view_ids else None if not module_views else str(module_views[0].get("view_id") or "")
        LOGGER.info(
            "Module navigation selected module view shell",
            extra={
                "selected_page": "module_view",
                "selected_module_id": module_id,
                "selected_module_view_id": next_view_id or "",
            },
        )
        st.session_state["selected_page"] = "module_view"
        st.session_state["selected_module_id"] = module_id
        st.session_state["selected_module_view_id"] = next_view_id
    st.rerun()


def _module_display_name(module: dict[str, object]) -> str:
    """Show the module's user-facing name without the legacy product prefix."""
    module_id = str(module.get("module_id") or "")
    module_name = str(module.get("name") or module_id or "Unnamed module")
    return module_name.removeprefix("Apmatia ")


def _set_theme_preference(theme: str) -> None:
    st.session_state["ui_theme_preference"] = theme
    st.rerun()


def _show_preferences() -> None:
    st.session_state["selected_page"] = "module_view"
    st.session_state["selected_module_id"] = "preferences"
    st.session_state["selected_module_view_id"] = "preferences.preferences.view"
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

    if nav in {"settings", "preferences"}:
        st.session_state["selected_page"] = "module_view"
        st.session_state["selected_module_id"] = "preferences"
        st.session_state["selected_module_view_id"] = "preferences.preferences.view"
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
        if st.button("⚙️ Preferences", key="header_preferences_button", use_container_width=True):
            _show_preferences()

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
    page_detail = None
    if selected_page == "module_view":
        module_id = str(st.session_state.get("selected_module_id") or "").strip()
        module_view_id = str(st.session_state.get("selected_module_view_id") or "").strip()
        page_detail = ":".join(part for part in (module_id, module_view_id) if part)
    page_generation = sync_page_generation(selected_page, detail=page_detail)
    LOGGER.info(
        "Rendering page",
        extra={
            "selected_page": selected_page,
            "selected_page_detail": page_detail or "",
            "page_generation": page_generation,
        },
    )

    with st.container(key=f"apm-page-shell:{selected_page}:{page_generation}"):
        if selected_page == "module_view":
            module_views.render()
            return

        if selected_page == "discussion":
            discussion.render()
            return

if __name__ == "__main__":
    main()
