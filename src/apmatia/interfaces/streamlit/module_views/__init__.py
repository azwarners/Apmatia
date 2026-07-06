"""Generic module view adapters for the Apmatia Streamlit interface."""

from apmatia.interfaces.streamlit.module_views.adapter import adapt_module_view
from apmatia.interfaces.streamlit.module_views.models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewIntent,
    ModuleViewNavigationPaneDescriptor,
    ModuleViewRenderModel,
)

__all__ = [
    "CollectionColumnDescriptor",
    "CollectionViewDescriptor",
    "ModuleViewActionDescriptor",
    "ModuleViewIntent",
    "ModuleViewNavigationPaneDescriptor",
    "ModuleViewRenderModel",
    "adapt_module_view",
]
