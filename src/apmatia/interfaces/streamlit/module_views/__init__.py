"""Generic module view adapters for the Apmatia Streamlit interface."""

from apmatia.core.view_contract.normalization import adapt_module_view
from apmatia.core.view_contract.models import (
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
