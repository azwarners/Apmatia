from __future__ import annotations

import streamlit as st

from apmatia.modules.persistence.logger import get_logger


_ACTIVE_PAGE_KEY = "_apm_streamlit_active_page"
_ACTIVE_PAGE_DETAIL_KEY = "_apm_streamlit_active_page_detail"
_PAGE_GENERATION_KEY = "_apm_streamlit_page_generation"
_LOGGER = get_logger(__name__)


def sync_page_generation(selected_page: str, *, detail: str | None = None) -> int:
    page = str(selected_page or "").strip()
    page_detail = str(detail or "").strip()
    signature = f"{page}:{page_detail}" if page_detail else page
    active_page = str(st.session_state.get(_ACTIVE_PAGE_KEY) or "").strip()
    active_detail = str(st.session_state.get(_ACTIVE_PAGE_DETAIL_KEY) or "").strip()
    generation = int(st.session_state.get(_PAGE_GENERATION_KEY) or 0)

    if page != active_page or page_detail != active_detail:
        generation += 1
        st.session_state[_PAGE_GENERATION_KEY] = generation
        st.session_state[_ACTIVE_PAGE_KEY] = page
        st.session_state[_ACTIVE_PAGE_DETAIL_KEY] = page_detail
        _LOGGER.info(
            "Page generation advanced",
            extra={
                "selected_page": page,
                "selected_page_detail": page_detail,
                "page_signature": signature,
                "page_generation": generation,
            },
        )
    elif _PAGE_GENERATION_KEY not in st.session_state:
        st.session_state[_PAGE_GENERATION_KEY] = generation
        st.session_state.setdefault(_ACTIVE_PAGE_KEY, page)
        st.session_state.setdefault(_ACTIVE_PAGE_DETAIL_KEY, page_detail)

    return generation


def current_page_generation() -> int:
    return int(st.session_state.get(_PAGE_GENERATION_KEY) or 0)


def is_current_page_generation(page_generation: int) -> bool:
    return current_page_generation() == int(page_generation)
