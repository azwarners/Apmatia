"""View descriptors for the Apmatia IPE module."""

from __future__ import annotations

from apmatia.core.registry import ViewContribution

from .collections import IPE_COLLECTION_VIEW_SPECS, IpeCollectionViewSpec

VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = tuple(
    ViewContribution(
        module_id="apmatia_ipe",
        action_id=spec.action_id,
        view_id=spec.view_id,
        name=f"{spec.plural_label} View",
        description=spec.description,
        metadata=spec.metadata,
    )
    for spec in IPE_COLLECTION_VIEW_SPECS
)
