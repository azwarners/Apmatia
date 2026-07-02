"""Model management page for CRUD operations on AI model configs."""
from __future__ import annotations

import streamlit as st

from apmatia.interfaces.streamlit.api_client import (
    ApiError,
    create_llm_config,
    delete_llm_config,
    list_llm_configs,
    test_llm_config,
    update_llm_config,
)


def _empty_form_values() -> dict[str, object]:
    return {
        "id": None,
        "user_alias": "",
        "backend": "openai_compatible",
        "provider_name": "",
        "model_url": "",
        "api_key": "",
        "max_response_size": 8192,
        "system_prompt": "",
    }


def _display_alias(config: dict[str, object]) -> str:
    return str(config.get("user_alias") or config.get("name") or "Unnamed config")


def _display_provider_name(config: dict[str, object]) -> str:
    return str(config.get("provider_name") or config.get("model_name") or "default")


def render() -> None:
    try:
        configs = list_llm_configs()
    except ApiError as error:
        st.error(f"Unable to load model configs: {error.detail}")
        return

    st.title("Model Management")
    st.caption("Create, edit, and remove AI model objects through the local API.")

    if "model_config_form_values" not in st.session_state:
        st.session_state["model_config_form_values"] = _empty_form_values()

    form_values = st.session_state["model_config_form_values"]
    with st.form("apmatia_model_config_form"):
        st.subheader("AI Model")
        left, right = st.columns(2)
        with left:
            user_alias = st.text_input("User alias", value=str(form_values["user_alias"]))
            backend = st.selectbox(
                "Backend",
                options=["openai_compatible", "koboldcpp"],
                index=0 if form_values["backend"] != "koboldcpp" else 1,
            )
            provider_name = st.text_input("Provider name", value=str(form_values["provider_name"]))
            max_response_size = st.number_input(
                "Max response size",
                min_value=1,
                step=256,
                value=int(form_values["max_response_size"]),
            )
        with right:
            model_url = st.text_input("Model URL", value=str(form_values["model_url"]))
            api_key = st.text_input("API key", value=str(form_values["api_key"]), type="password")
            system_prompt = st.text_area(
                "System prompt",
                value=str(form_values["system_prompt"]),
                height=160,
            )

        submitted = st.form_submit_button("Save config")

    if submitted:
        payload = {
            "user_alias": user_alias,
            "backend": backend,
            "provider_name": provider_name,
            "model_url": model_url,
            "api_key": api_key,
            "max_response_size": int(max_response_size),
            "system_prompt": system_prompt,
            "metadata": {},
        }
        current_id = form_values.get("id")
        try:
            if current_id is None:
                create_llm_config(**payload)
            else:
                update_llm_config(int(current_id), **payload)
        except ApiError as error:
            st.error(f"Unable to save model config: {error.detail}")
        else:
            st.success("Model config saved.")
            st.session_state["model_config_form_values"] = _empty_form_values()
            st.rerun()

    st.divider()
    st.subheader("Existing AI models")
    if not configs:
        st.info("No AI models have been created yet.")
        return

    for config in configs:
        with st.container(border=True):
            st.write(f"**{_display_alias(config)}**")
            st.caption(
                f"ID {config.get('id')} · {config.get('backend')} · {_display_provider_name(config)}"
            )
            model_url = str(config.get("model_url") or "").strip()
            if model_url:
                st.caption(f"URL: {model_url}")
            edit_col, test_col, delete_col = st.columns(3)
            with edit_col:
                if st.button("Edit", key=f"edit_model_config_{config.get('id')}"):
                    st.session_state["model_config_form_values"] = dict(config)
                    st.rerun()
            with test_col:
                if st.button("Test", key=f"test_model_config_{config.get('id')}"):
                    try:
                        result = test_llm_config(int(config.get("id")))
                    except ApiError as error:
                        st.error(f"Unable to test AI model: {error.detail}")
                    else:
                        st.success(
                            f"AI model responded: {result.get('reply_preview', '')}"
                        )
            with delete_col:
                if st.button("Delete", key=f"delete_model_config_{config.get('id')}"):
                    try:
                        delete_llm_config(int(config.get("id")))
                    except ApiError as error:
                        st.error(f"Unable to delete model config: {error.detail}")
                    else:
                        st.success("AI model deleted.")
                        st.rerun()
