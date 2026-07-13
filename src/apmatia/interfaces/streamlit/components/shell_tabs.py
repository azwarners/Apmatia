"""Top-of-page shell tab strip for Streamlit views."""
from __future__ import annotations


def render_shell_tabs(
    options: tuple[str, ...],
    *,
    key: str,
    default: str,
) -> str:
    import streamlit as st

    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] {
            position: fixed !important;
            top: 0.35rem !important;
            left: max(22.5rem, 22vw) !important;
            right: 1rem !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            z-index: 2147483646 !important;
        }

        div[data-testid="stRadio"] > div {
            flex-wrap: wrap;
            gap: 0.35rem 1rem;
            background: transparent;
        }

        div[data-testid="stRadio"] label {
            margin-bottom: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    try:
        index = options.index(default)
    except ValueError:
        index = 0
    return str(
        st.radio(
            "Shell view",
            options=options,
            index=index,
            horizontal=True,
            key=key,
            label_visibility="collapsed",
        )
    )
