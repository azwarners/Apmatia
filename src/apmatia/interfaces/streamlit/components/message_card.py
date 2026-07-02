"""Reusable message card component for chat-style Streamlit pages."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from apmatia.interfaces.streamlit.components.clipboard_button import (
    apply_clipboard_button_css,
    render_clipboard_button,
)


@dataclass(frozen=True)
class MessageCardActions:
    """Optional handlers for the standard message card actions."""

    on_copy: Callable[[str], None] | None = None
    on_edit: Callable[[str], None] | None = None
    on_delete: Callable[[str], None] | None = None


@dataclass(frozen=True)
class MessageActionSpec:
    """Definition for one action button in the footer row."""

    key: str
    icon: str
    label: str
    callback: Callable[[str], None]


def render_message_text_block(text: str) -> None:
    """Render message text with Streamlit markdown so emoji and formatting work."""
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    st.markdown(normalized_text)


def apply_message_card_css() -> None:
    """Inject shared styling for message cards and their hover actions."""
    apply_clipboard_button_css()
    st.html(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            max-width: 100%;
            box-sizing: border-box;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] {
            background: rgba(255, 255, 255, 0.045);
            border-radius: 0.75rem;
            margin: 0.35rem 0 0;
            padding: 0.95rem 1rem;
            font-family: var(
                --apm-message-font-family,
                var(--apm-font-family, system-ui)
            ), "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
            line-height: 1.55;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > div {
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] ul,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] ol,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] blockquote,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] pre {
            margin-bottom: 0.75rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p:last-child,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] ul:last-child,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] ol:last-child,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] blockquote:last-child,
        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] pre:last-child {
            margin-bottom: 0;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer button {
            min-height: 1.8rem;
            min-width: 1.8rem;
            padding: 0.1rem 0.25rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer {
            width: 100%;
            padding: 0;
            opacity: 0;
            pointer-events: none;
            transition: opacity 120ms ease-in-out;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover .apm-message-footer {
            opacity: 1;
            pointer-events: auto;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer [data-testid="stHorizontalBlock"] {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            flex-wrap: nowrap;
            width: 100%;
            padding: 0;
            margin: 0;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer [data-testid="stHorizontalBlock"] > div {
            flex: 0 0 auto !important;
            min-width: 0;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer [data-testid="stHorizontalBlock"] > div > div {
            gap: 0 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .apm-message-footer [data-testid="stHorizontalBlock"] button {
            margin: 0;
        }
        </style>
        """,
    )


def render_message_actions(
    *,
    message_text: str,
    copy_key: str,
    edit_key: str,
    delete_key: str,
    actions: MessageCardActions | None = None,
) -> None:
    """Render the standard message action buttons."""
    actions = actions or MessageCardActions()
    action_specs: list[MessageActionSpec | None] = [
        MessageActionSpec(copy_key, "", "Copy", actions.on_copy)
        if actions.on_copy is not None
        else None,
        MessageActionSpec(edit_key, ":material/edit:", "Edit", actions.on_edit)
        if actions.on_edit is not None
        else None,
        MessageActionSpec(delete_key, ":material/delete:", "Delete", actions.on_delete)
        if actions.on_delete is not None
        else None,
    ]
    action_specs = [spec for spec in action_specs if spec is not None]

    if not action_specs:
        return

    with st.container(horizontal=True, horizontal_alignment="right", gap="medium"):
        for spec in action_specs:
            if spec.label == "Copy":
                render_clipboard_button(message_text, spec.key, aria_label="Copy message")
                continue
            if st.button(
                " ",
                key=spec.key,
                icon=spec.icon,
                type="tertiary",
                width="content",
                help=spec.label,
            ):
                spec.callback(message_text)


def render_message_card(
    *,
    title: str,
    message_text: str,
    card_key: str,
    subtitle: str | None = None,
    actions: MessageCardActions | None = None,
    content: Callable[[], None] | None = None,
    details: Callable[[], None] | None = None,
    details_label: str = "Details",
) -> None:
    """Render a reusable bordered chat/message card."""
    with st.container(border=True):
        st.caption(title)
        if subtitle:
            st.caption(subtitle)
        if content is None:
            render_message_text_block(message_text)
        else:
            content()
        if details is not None:
            with st.expander(details_label, expanded=False):
                details()

        st.markdown('<div class="apm-message-footer">', unsafe_allow_html=True)
        render_message_actions(
            message_text=message_text,
            copy_key=f"{card_key}-copy",
            edit_key=f"{card_key}-edit",
            delete_key=f"{card_key}-delete",
            actions=actions,
        )
        st.markdown("</div>", unsafe_allow_html=True)
