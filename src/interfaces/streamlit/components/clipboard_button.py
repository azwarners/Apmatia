"""Reusable browser-side clipboard button for Streamlit pages."""
from __future__ import annotations

import base64
import hashlib
import html
import json


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


def render_clipboard_image_paste_bridge(
    key: str,
    *,
    target_selector: str = 'input[type="file"]',
    aria_label: str = "Paste screenshots from clipboard",
) -> None:
    """Bind a browser paste handler that appends image clipboard items to a file input."""
    import streamlit as st

    element_id = "apmatia-paste-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    st.html(
        f"""
        <div
            id="{html.escape(element_id)}"
            class="apmatia-paste-bridge"
            aria-label="{html.escape(aria_label)}"
            aria-hidden="true"
        ></div>

        <script>
        (() => {{
            const root = document.getElementById("{element_id}");
            const globalKey = "__apmatiaClipboardPasteBridgeBound";
            if (!root || window[globalKey] === true) return;
            window[globalKey] = true;

            const fileInputSelector = {json.dumps(target_selector)};

            const findUploaderInput = () => {{
                const inputs = Array.from(document.querySelectorAll(fileInputSelector));
                return (
                    inputs.find(
                        (input) =>
                            input instanceof HTMLInputElement &&
                            !input.disabled &&
                            Boolean(input.closest('[data-testid="stFileUploader"]'))
                    ) || null
                );
            }};

            const mimeToExtension = (mimeType) => {{
                switch ((mimeType || "").toLowerCase()) {{
                    case "image/jpeg":
                    case "image/jpg":
                        return "jpg";
                    case "image/webp":
                        return "webp";
                    case "image/gif":
                        return "gif";
                    case "image/png":
                    default:
                        return "png";
                }}
            }};

            const makeFileName = (mimeType, index) =>
                `pasted-screenshot-${{Date.now()}}-${{index + 1}}.${{mimeToExtension(mimeType)}}`;

            const extractImages = (event) => {{
                const clipboard = event.clipboardData;
                if (!clipboard) return [];

                const imageFiles = [];
                for (const item of Array.from(clipboard.items || [])) {{
                    if (item.kind !== "file" || !item.type || !item.type.startsWith("image/")) {{
                        continue;
                    }}
                    const file = item.getAsFile();
                    if (file) imageFiles.push(file);
                }}

                if (!imageFiles.length) {{
                    for (const file of Array.from(clipboard.files || [])) {{
                        if (file && file.type && file.type.startsWith("image/")) {{
                            imageFiles.push(file);
                        }}
                    }}
                }}

                return imageFiles;
            }};

            const dispatchUploaderUpdate = (input) => {{
                input.dispatchEvent(new Event("input", {{ bubbles: true }}));
                input.dispatchEvent(new Event("change", {{ bubbles: true }}));
            }};

            const attachFiles = (files) => {{
                const input = findUploaderInput();
                if (!input) return false;

                const dataTransfer = new DataTransfer();
                for (const existingFile of Array.from(input.files || [])) {{
                    dataTransfer.items.add(existingFile);
                }}
                for (const file of files) {{
                    dataTransfer.items.add(file);
                }}

                input.files = dataTransfer.files;
                dispatchUploaderUpdate(input);
                return true;
            }};

            const handler = (event) => {{
                const images = extractImages(event);
                if (!images.length) return;

                const files = images.map(
                    (file, index) =>
                        new File([file], makeFileName(file.type, index), {{
                            type: file.type || "image/png",
                            lastModified: Date.now(),
                        }})
                );

                if (attachFiles(files)) {{
                    event.preventDefault();
                    event.stopPropagation();
                }}
            }};

            document.addEventListener("paste", handler, true);
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
