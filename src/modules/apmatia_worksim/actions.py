"""Action descriptors for the Apmatia Worksim module."""

from __future__ import annotations

from src.core.registry import ActionContribution

from .views import ORG_CHART_VIEW_SPECS


ACTION_DESCRIPTORS: tuple[ActionContribution, ...] = tuple(
    ActionContribution(
        module_id="apmatia_worksim",
        action_id=spec.action_id,
        name=f"{spec.plural_label} Action",
        description=spec.description,
        metadata={
            "object_type": spec.object_type,
            "collection_view_id": spec.view_id,
        },
    )
    for spec in ORG_CHART_VIEW_SPECS
)
