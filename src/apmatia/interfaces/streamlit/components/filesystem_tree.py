"""Lightweight filesystem tree rendering for Streamlit pages."""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st


def render_filesystem_tree(root: str | Path, *, label: str, max_depth: int = 2) -> None:
    root_path = Path(root).expanduser()
    st.subheader(label)
    st.caption(str(root_path))
    if not root_path.exists():
        st.info("This directory does not exist yet.")
        return
    if not root_path.is_dir():
        st.warning("This path is not a directory.")
        return

    st.markdown(
        f"<div class='apm-filesystem-tree'>{_build_tree_html(root_path, current_depth=0, max_depth=max_depth)}</div>",
        unsafe_allow_html=True,
    )


def _build_tree_html(path: Path, *, current_depth: int, max_depth: int) -> str:
    name = html.escape(path.name or str(path))
    if path.is_file():
        return f"<div class='apm-tree-leaf'>📄 {name}</div>"

    try:
        children = sorted(path.iterdir(), key=_tree_sort_key)
    except OSError:
        return f"<details open><summary>📁 {name}</summary><div class='apm-tree-leaf'>Unable to read directory.</div></details>"

    if current_depth >= max_depth:
        return f"<details open><summary>📁 {name}</summary><div class='apm-tree-leaf'>Tree truncated at depth {max_depth}.</div></details>"

    child_html = "".join(
        _build_tree_html(child, current_depth=current_depth + 1, max_depth=max_depth)
        for child in children
    )
    child_count = len(children)
    empty_node = "<div class='apm-tree-leaf'>Empty directory.</div>"
    return (
        f"<details{' open' if current_depth == 0 else ''}>"
        f"<summary>📁 {name} <span class='apm-tree-meta'>{child_count} item{'s' if child_count != 1 else ''}</span></summary>"
        f"<div class='apm-tree-children'>{child_html or empty_node}</div>"
        "</details>"
    )


def _tree_sort_key(path: Path) -> tuple[int, str]:
    if path.is_dir():
        return (0, path.name.lower())
    return (1, path.name.lower())
