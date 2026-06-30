"""Action descriptors for the Apmatia IPE module."""

from __future__ import annotations

from src.core.registry import ActionContribution

from .views import IPE_COLLECTION_VIEW_SPECS


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = tuple(
    ActionContribution(
        module_id="apmatia_ipe",
        action_id=spec.action_id,
        name=f"{spec.plural_label} Action",
        description=spec.description,
        metadata={
            "object_type": spec.object_type,
            "collection_view_id": spec.view_id,
        },
    )
    for spec in IPE_COLLECTION_VIEW_SPECS
)
