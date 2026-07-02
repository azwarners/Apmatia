from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from apmatia.core.registry import ViewContribution
from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.models import ModuleViewIntent
from apmatia.interfaces.streamlit.module_views.renderers import render_module_view


def render_module_view_page(
    view: ViewContribution | dict[str, Any],
    *,
    items: Sequence[Any] | None = None,
    on_intent: Callable[[ModuleViewIntent], None] | None = None,
) -> list[ModuleViewIntent]:
    spec = adapt_module_view(view, items=items)
    return render_module_view(spec, on_intent=on_intent)
