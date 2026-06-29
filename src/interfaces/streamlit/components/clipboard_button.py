"""Reusable browser-side clipboard button for Streamlit pages."""
from __future__ import annotations

import base64
import hashlib
import html


def render_clipboard_button(text: str, key: str, *, aria_label: str = "Copy text") -> None:
    """Render a main-DOM JavaScript copy button that can reach the browser clipboard."""
    import streamlit as st

    element_id = "apmatia-copy-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")

    st.html(
        f"""
        <button
            id="{html.escape(element_id)}"
            class="apmatia-copy-button"
            type="button"
            title="Copy"
            aria-label="{html.escape(aria_label)}"
            data-copy="{payload}"
        >
            <span class="apmatia-copy-glyph" aria-hidden="true"></span>
        </button>

        <script>
        (() => {{
            const button = document.getElementById("{element_id}");
            if (!button || button.dataset.bound === "true") return;
            button.dataset.bound = "true";

            const icon = button.querySelector("span");

            button.addEventListener("click", async () => {{
                const binary = atob(button.dataset.copy);
                const bytes = Uint8Array.from(
                    binary,
                    character => character.charCodeAt(0)
                );
                const text = new TextDecoder().decode(bytes);

                try {{
                    await navigator.clipboard.writeText(text);
                    icon.classList.add("is-copied");
                    button.title = "Copied";

                    setTimeout(() => {{
                        icon.classList.remove("is-copied");
                        button.title = "Copy";
                    }}, 1500);
                }} catch (error) {{
                    console.error("Clipboard write failed", error);
                    button.title = "Copy failed";
                }}
            }});
        }})();
        </script>
        """,
        width="content",
        unsafe_allow_javascript=True,
    )


def apply_clipboard_button_css() -> None:
    """Inject shared styling for the custom clipboard button."""
    import streamlit as st

    st.html(
        """
        <style>
        [data-testid="stCodeCopyButton"] {
            display: none !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCodeBlock"] button {
            display: none !important;
        }

        .apmatia-copy-button {
            align-items: center;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 6px;
            color: inherit;
            cursor: pointer;
            display: inline-flex;
            height: 2.5rem;
            justify-content: center;
            padding: 0 0.75rem;
        }

        .apmatia-copy-button:hover {
            border-color: currentColor;
        }

        .apmatia-copy-glyph {
            display: block;
            height: 16px;
            position: relative;
            width: 16px;
        }

        .apmatia-copy-glyph::before,
        .apmatia-copy-glyph::after {
            border: 1.7px solid currentColor;
            border-radius: 2px;
            content: "";
            height: 9px;
            position: absolute;
            width: 9px;
        }

        .apmatia-copy-glyph::before {
            left: 1px;
            top: 1px;
        }

        .apmatia-copy-glyph::after {
            background: var(--apm-bg, #0e1117);
            left: 5px;
            top: 5px;
        }

        .apmatia-copy-glyph.is-copied::before {
            border-left: 0;
            border-top: 0;
            border-radius: 0;
            height: 11px;
            left: 6px;
            top: 0;
            transform: rotate(45deg);
            width: 5px;
        }

        .apmatia-copy-glyph.is-copied::after {
            display: none;
        }
        </style>
        """,
    )
