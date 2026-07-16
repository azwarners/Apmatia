"""View descriptors for the Apmatia Worksim module."""

from __future__ import annotations

from apmatia.core.registry import ViewContribution

from .collections import ORG_CHART_VIEW_SPECS, WorksimOrgChartViewSpec

VIEW_DESCRIPTORS: tuple[ViewContribution, ...] = tuple(
    ViewContribution(
        module_id="worksim",
        action_id=spec.action_id,
        view_id=spec.view_id,
        name="Org Chart View",
        description=spec.description,
        metadata=spec.metadata,
    )
    for spec in ORG_CHART_VIEW_SPECS
)
