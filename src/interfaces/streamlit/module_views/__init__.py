"""Generic module view adapters for the Apmatia Streamlit interface."""

from src.interfaces.streamlit.module_views.adapter import adapt_module_view
from src.interfaces.streamlit.module_views.models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewIntent,
    ModuleViewRenderModel,
)

__all__ = [
    "CollectionColumnDescriptor",
    "CollectionViewDescriptor",
    "ModuleViewActionDescriptor",
    "ModuleViewIntent",
    "ModuleViewRenderModel",
    "adapt_module_view",
]
