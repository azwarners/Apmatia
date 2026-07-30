"""Compatibility exports for the framework-neutral view contract.

New interfaces and modules must import these types from ``apmatia.core.view_contract``.
"""

from apmatia.core.view_contract.models import (
    CollectionColumnDescriptor,
    CollectionViewDescriptor,
    ModuleViewActionDescriptor,
    ModuleViewFormActionDescriptor,
    ModuleViewFormDescriptor,
    ModuleViewFormFieldDescriptor,
    ModuleViewIntent,
    ModuleViewNavigationPaneDescriptor,
    ModuleViewRenderModel,
)

__all__ = [
    "CollectionColumnDescriptor",
    "CollectionViewDescriptor",
    "ModuleViewActionDescriptor",
    "ModuleViewFormActionDescriptor",
    "ModuleViewFormDescriptor",
    "ModuleViewFormFieldDescriptor",
    "ModuleViewIntent",
    "ModuleViewNavigationPaneDescriptor",
    "ModuleViewRenderModel",
]
