"""Shared tutor page helpers."""
from __future__ import annotations

import streamlit as st

from collections.abc import Callable

from apmatia.interfaces.streamlit.api_client import ApiError, search_wiki
from apmatia.interfaces.streamlit.pages import discussion as discussion_page


def wiki_label(wiki: dict[str, object]) -> str:
    wiki_id = wiki.get("id")
    title = wiki.get("title") or "Untitled Wiki"
    return f"{title} (ID {wiki_id})"


def find_discussion(discussions: list[dict[str, object]], discussion_id: object) -> dict[str, object] | None:
    for discussion in discussions:
        if str(discussion.get("discussion_id")) == str(discussion_id):
            return discussion
    return None


def is_saved_tutor_discussion(discussion: dict[str, object]) -> bool:
    focused_wiki_id = discussion.get("focused_wiki_id")
    if focused_wiki_id is None:
        return False
    return bool(str(focused_wiki_id).strip())


def find_node(tree_node: dict[str, object], node_id: str) -> dict[str, object] | None:
    if str(tree_node.get("id")) == str(node_id):
        return tree_node
    for child in tree_node.get("children", []):
        found = find_node(child, node_id)
        if found is not None:
            return found
    return None


def ensure_selected_node(tree: dict[str, object]) -> dict[str, object]:
    root = tree["root"]
    selected_node_id = st.session_state.get("tutor_selected_node_id")
    selected = find_node(root, str(selected_node_id)) if selected_node_id else None
    if selected is None:
        st.session_state["tutor_selected_node_id"] = root["id"]
        return root
    return selected


def render_tree(node: dict[str, object], *, selected_node_id: str) -> None:
    st.markdown(
        f"<div class='tree-shell'><ul class='tree'>{build_tree_html(node, selected_node_id=selected_node_id)}</ul></div>",
        unsafe_allow_html=True,
    )


def build_tree_html(node: dict[str, object], *, selected_node_id: str) -> str:
    node_id = str(node.get("id"))
    title = str(node.get("title", "Untitled"))
    node_type = str(node.get("node_type", "branch"))
    child_count = len(node.get("children", []))
    selected_class = " is-selected" if node_id == selected_node_id else ""

    if node_type == "leaf":
        return (
            f"<li class='tree-item tree-leaf{selected_class}' data-node-id='{node_id}'>"
            f"<span class='tree-leaf-label'>📄 {title}</span>"
            "</li>"
        )

    children_html = "".join(
        build_tree_html(child, selected_node_id=selected_node_id)
        for child in node.get("children", [])
    )
    open_attr = " open" if str(node.get("parent_id")) in {"None", "", "null"} else ""
    return (
        f"<li class='tree-item tree-branch{selected_class}' data-node-id='{node_id}'>"
        f"<details{open_attr}>"
        f"<summary><span class='tree-branch-label'>📁 {title}</span><span class='tree-branch-meta'>{child_count} child{'ren' if child_count != 1 else ''}</span></summary>"
        f"<ul>{children_html}</ul>"
        "</details>"
        "</li>"
    )


def render_wiki_summary(wiki: dict[str, object]) -> None:
    st.subheader("Focused wiki")
    st.caption(f"Building notes in: {wiki['title']}")
    if wiki.get("description"):
        st.write(str(wiki["description"]))


def render_wiki_search(wiki: dict[str, object]) -> None:
    query = st.text_input("Search this wiki", key="tutor_wiki_search_query")
    if query.strip():
        try:
            results = search_wiki(str(wiki["id"]), query.strip())
        except ApiError as error:
            st.error(f"Unable to search wiki: {error.detail}")
        else:
            if results:
                st.caption(f"Found {len(results)} matching note(s).")
                for result in results[:8]:
                    if st.button(result["path"], key=f"tutor-search-{result['id']}", use_container_width=True):
                        st.session_state["tutor_selected_node_id"] = result["id"]
                        st.rerun()
            else:
                st.info("No wiki matches yet.")


def discussion_controls(selected_agent: dict[str, object], model_lookup: dict[int, dict[str, object]]) -> None:
    model_summary = discussion_page._selected_model_summary(selected_agent, model_lookup)
    if model_summary:
        st.caption(model_summary)


def get_tutor_selected_agent_id(default: object | None = None) -> object | None:
    if "tutor_selected_agent_id" in st.session_state:
        return st.session_state.get("tutor_selected_agent_id")
    return default


def build_tutor_wiki_context(wiki: dict[str, object], selected_node: dict[str, object] | None = None) -> str:
    root_node_id = str(wiki.get("root_node_id") or "")
    selected_node_id = "" if selected_node is None else str(selected_node.get("id") or "")
    selected_title = "" if selected_node is None else str(selected_node.get("title") or "")
    lines = [
        "Tutor session wiki context:",
        f"- wiki_id: {wiki.get('id')}",
        f"- wiki_title: {wiki.get('title') or 'Untitled Wiki'}",
        f"- root_node_id: {root_node_id or 'unknown'}",
    ]
    if selected_node is not None:
        lines.append(f"- selected_node_id: {selected_node_id or 'unknown'}")
        lines.append(f"- selected_node_title: {selected_title or 'Untitled'}")
    lines.extend(
        [
            "The wiki is already attached to this tutor session.",
            "Use the provided wiki_id/root_node_id directly.",
            "Do not ask the user to provide a wiki ID or guess the parent node.",
            "When creating a top-level section, use the root_node_id as parent_id unless the user selects a different branch.",
        ]
    )
    return "\n".join(lines)


def apply_wiki_tree_css() -> None:
    st.html(
        """
        <style>
        .tree-shell {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--apm-border);
          border-radius: 16px;
          padding: 0.75rem 0.85rem;
        }

        .tree-shell .tree {
          --spacing: 1.35rem;
          --radius: 10px;
          padding-left: 0;
          margin: 0;
        }

        .tree-shell .tree li,
        .tree-shell .tree-item {
          display: block;
          position: relative;
          padding-left: calc(2 * var(--spacing) - var(--radius) - 2px);
          list-style: none;
        }

        .tree-shell .tree ul {
          margin-left: calc(var(--radius) - var(--spacing));
          padding-left: 0;
        }

        .tree-shell .tree ul li {
          border-left: 2px solid var(--apm-border);
        }

        .tree-shell .tree ul li:last-child {
          border-color: transparent;
        }

        .tree-shell .tree ul li::before {
          content: '';
          display: block;
          position: absolute;
          top: calc(var(--spacing) / -2);
          left: -2px;
          width: calc(var(--spacing) + 2px);
          height: calc(var(--spacing) + 1px);
          border: solid var(--apm-border);
          border-width: 0 0 2px 2px;
        }

        .tree-shell .tree summary {
          display: block;
          cursor: pointer;
          list-style: none;
          padding: 0.2rem 0.15rem 0.3rem;
          position: relative;
        }

        .tree-shell .tree summary::-webkit-details-marker {
          display: none;
        }

        .tree-shell .tree summary:focus {
          outline: none;
        }

        .tree-shell .tree summary:focus-visible {
          outline: 1px dotted var(--apm-text);
        }

        .tree-shell .tree summary::after {
          content: '›';
          position: absolute;
          left: 0.1rem;
          top: 50%;
          transform: translateY(-50%) rotate(0deg);
          color: var(--apm-muted);
          font-size: 1.15rem;
          line-height: 1;
          font-weight: 500;
        }

        .tree-shell .tree details[open] > summary::after {
          transform: translateY(-50%) rotate(90deg);
          color: var(--apm-accent);
        }

        .tree-shell .tree-branch-label,
        .tree-shell .tree-leaf-label {
          font-weight: 600;
          padding-left: 1.1rem;
        }

        .tree-shell .tree-branch-meta {
          color: var(--apm-muted);
          font-size: 0.78rem;
          margin-left: 0.35rem;
        }

        .tree-shell .tree-branch.is-selected > details > summary .tree-branch-label,
        .tree-shell .tree-leaf.is-selected .tree-leaf-label {
          color: var(--apm-accent);
        }

        .tree-shell .tree-leaf {
          padding-left: 1.45rem;
          margin: 0.15rem 0;
        }

        .tree-shell .tree-leaf::before {
          content: '';
          position: absolute;
          left: 0.55rem;
          top: 0.9rem;
          width: 0.55rem;
          height: 1px;
          background: var(--apm-border);
        }

        .tree-shell .tree-leaf-label {
          display: inline-flex;
          gap: 0.35rem;
          align-items: center;
          color: var(--apm-text);
        }

        .tree-shell .tree details > summary:hover .tree-branch-label,
        .tree-shell .tree details > summary:hover .tree-branch-meta {
          color: var(--apm-text);
        }
        </style>
        """,
    )
