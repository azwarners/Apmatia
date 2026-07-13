"""Reusable terminal-style output block for Streamlit pages."""
from __future__ import annotations

from html import escape


def render_terminal_block(
    title: str,
    body: str,
    *,
    subtitle: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
    status: str | None = None,
    body_height: str | int = "content",
) -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at top right, rgba(157, 255, 173, 0.10), transparent 34%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(0, 0, 0, 0)),
                var(--apm-terminal-bg, #000000);
            border: 1px solid var(--apm-terminal-border, rgba(110, 255, 170, 0.35));
            box-shadow:
                0 0 0 1px rgba(157, 255, 173, 0.04),
                0 0 26px rgba(0, 0, 0, 0.35),
                inset 0 0 28px rgba(157, 255, 173, 0.04);
        }

        div[data-testid="stVerticalBlockBorderWrapper"]::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 13%),
                repeating-linear-gradient(
                    180deg,
                    rgba(157, 255, 173, 0.022) 0px,
                    rgba(157, 255, 173, 0.022) 1px,
                    transparent 1px,
                    transparent 4px
                );
            opacity: 0.34;
            mix-blend-mode: screen;
        }

        .apm-terminal-shell {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
            height: 100%;
            min-height: 0;
            padding: 0.55rem 0.75rem 0.45rem;
        }

        .apm-terminal-chrome {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            color: var(--apm-terminal-muted, rgba(157, 255, 173, 0.72));
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .apm-terminal-chrome-left {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            min-width: 0;
        }

        .apm-terminal-dots {
            display: inline-flex;
            align-items: center;
            gap: 0.28rem;
            flex: 0 0 auto;
        }

        .apm-terminal-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 999px;
            background: var(--apm-terminal-muted, rgba(157, 255, 173, 0.72));
            box-shadow: 0 0 12px rgba(157, 255, 173, 0.18);
            opacity: 0.8;
        }

        .apm-terminal-title {
            color: var(--apm-terminal-text, #9dffad);
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .apm-terminal-status {
            flex: 0 0 auto;
            padding: 0.22rem 0.55rem;
            border: 1px solid var(--apm-terminal-border, rgba(110, 255, 170, 0.35));
            border-radius: 999px;
            color: var(--apm-terminal-text, #9dffad);
            background: rgba(157, 255, 173, 0.06);
            white-space: nowrap;
        }

        .apm-terminal-meta {
            display: grid;
            gap: 0.25rem;
            color: var(--apm-terminal-muted, rgba(157, 255, 173, 0.72));
            font-size: 0.77rem;
        }

        .apm-terminal-prompt {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            color: var(--apm-terminal-text, #9dffad);
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace !important;
            letter-spacing: 0.01em;
        }

        .apm-terminal-prompt-prefix {
            color: var(--apm-terminal-muted, rgba(157, 255, 173, 0.72));
        }

        .apm-terminal-cursor {
            display: inline-block;
            width: 0.65ch;
            height: 1.1em;
            background: var(--apm-terminal-text, #9dffad);
            box-shadow: 0 0 12px rgba(157, 255, 173, 0.35);
            animation: apm-terminal-blink 1.05s steps(1, end) infinite;
            transform: translateY(0.15em);
        }

        @keyframes apm-terminal-blink {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }

        .apm-terminal-subtitle {
            color: var(--apm-terminal-muted, rgba(157, 255, 173, 0.72));
        }

        .apm-terminal-body {
            flex: 1 1 auto;
            min-height: 0;
            overflow: auto;
            padding: 0.9rem 1rem;
            border-radius: 0.55rem;
            border: 1px solid rgba(157, 255, 173, 0.12);
            background: #000000;
            color: var(--apm-terminal-text, #9dffad);
            box-shadow:
                inset 0 0 0 1px rgba(157, 255, 173, 0.08),
                inset 0 0 28px rgba(0, 0, 0, 0.26);
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace !important;
            font-size: 0.93rem;
            line-height: 1.55;
            white-space: pre-wrap;
            word-break: break-word;
            overflow-wrap: anywhere;
            text-shadow: 0 0 8px rgba(157, 255, 173, 0.12);
        }

        .apm-terminal-body,
        .apm-terminal-body * {
            color: var(--apm-terminal-text, #9dffad) !important;
        }

        .apm-terminal-body::selection,
        .apm-terminal-body *::selection {
            background: rgba(157, 255, 173, 0.24);
            color: #000000;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    container_height = body_height if isinstance(body_height, int) or body_height == "stretch" else "content"
    with st.container(border=True, height=container_height):
        shell_title = escape(title)
        shell_status = escape(status or ("LIVE" if subtitle else "SESSION"))
        shell_subtitle = escape(subtitle) if subtitle else ""
        shell_prompt = escape(prompt) if prompt else ""
        body_language_class = f" apm-terminal-language-{escape(language)}" if language else ""
        st.markdown(
            f"""
            <div class="apm-terminal-shell{body_language_class}">
                <div class="apm-terminal-chrome">
                    <div class="apm-terminal-chrome-left">
                        <span class="apm-terminal-dots" aria-hidden="true">
                            <span class="apm-terminal-dot"></span>
                            <span class="apm-terminal-dot"></span>
                            <span class="apm-terminal-dot"></span>
                        </span>
                        <span class="apm-terminal-title">{shell_title}</span>
                    </div>
                    <span class="apm-terminal-status">{shell_status}</span>
                </div>
                <div class="apm-terminal-meta">
                    {f'<div class="apm-terminal-prompt"><span class="apm-terminal-prompt-prefix">{shell_prompt}</span><span class="apm-terminal-cursor" aria-hidden="true"></span></div>' if shell_prompt else ""}
                    {f'<div class="apm-terminal-subtitle">{shell_subtitle}</div>' if shell_subtitle else ""}
                </div>
                <div class="apm-terminal-body">{escape(body or "")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
