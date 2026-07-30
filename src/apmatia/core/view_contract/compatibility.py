from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    SUPPORTED_COMPONENT_TYPES,
    SUPPORTED_DATA_SOURCE_KINDS,
    SUPPORTED_EFFECT_TYPES,
    SUPPORTED_FIELD_TYPES,
    VIEW_CONTRACT_VERSION,
    ViewComponent,
    ViewDocument,
)
from .validation import ViewContractIssue, validate_view_document


@dataclass(frozen=True, slots=True)
class RendererCapabilities:
    renderer_id: str
    supported_versions: tuple[int, ...] = (VIEW_CONTRACT_VERSION,)
    component_types: frozenset[str] = field(default_factory=lambda: SUPPORTED_COMPONENT_TYPES)
    effect_types: frozenset[str] = field(default_factory=lambda: SUPPORTED_EFFECT_TYPES)
    field_types: frozenset[str] = field(default_factory=lambda: SUPPORTED_FIELD_TYPES)
    data_source_kinds: frozenset[str] = field(default_factory=lambda: SUPPORTED_DATA_SOURCE_KINDS)
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class NegotiatedViewContract:
    renderer_id: str
    schema_version: int
    document: ViewDocument


class ViewContractCompatibilityError(ValueError):
    def __init__(self, issues: list[ViewContractIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("Incompatible view renderer: " + "; ".join(str(issue) for issue in issues))


def negotiate_view_contract(
    document: ViewDocument,
    renderer: RendererCapabilities,
) -> NegotiatedViewContract:
    """Validate a document and prove that a renderer can honor every required semantic feature."""
    root = f"views[{document.view_id}]"
    issues: list[ViewContractIssue] = []
    if document.schema_version not in renderer.supported_versions:
        issues.append(
            ViewContractIssue(
                f"{root}.schema_version",
                f"renderer {renderer.renderer_id} supports {renderer.supported_versions}, not {document.schema_version}",
            )
        )
    if issues:
        raise ViewContractCompatibilityError(issues)
    validate_view_document(document)
    for path, component in _components(document.presentation, f"{root}.presentation"):
        if component.component_type not in renderer.component_types:
            issues.append(
                ViewContractIssue(
                    f"{path}.component_type",
                    f"renderer {renderer.renderer_id} does not support {component.component_type}",
                )
            )
        if component.component_type == "field":
            field_type = str(component.properties.get("field_type") or "text")
            if field_type not in renderer.field_types:
                issues.append(
                    ViewContractIssue(
                        f"{path}.properties.field_type",
                        f"renderer {renderer.renderer_id} does not support field type {field_type}",
                    )
                )
    for index, source in enumerate(document.data_sources):
        if source.kind not in renderer.data_source_kinds:
            issues.append(
                ViewContractIssue(
                    f"{root}.data_sources[{index}].kind",
                    f"renderer {renderer.renderer_id} does not support {source.kind}",
                )
            )
    all_effects = list(document.effects)
    for action in document.actions:
        all_effects.extend(action.success_effects)
        all_effects.extend(action.failure_effects)
    for index, effect in enumerate(all_effects):
        if effect.effect_type not in renderer.effect_types:
            issues.append(
                ViewContractIssue(
                    f"{root}.effects[{index}].effect_type",
                    f"renderer {renderer.renderer_id} does not support {effect.effect_type}",
                )
            )
    for capability in document.required_renderer_capabilities:
        if capability not in renderer.capabilities:
            issues.append(
                ViewContractIssue(
                    f"{root}.required_renderer_capabilities",
                    f"renderer {renderer.renderer_id} is missing capability: {capability}",
                )
            )
    if issues:
        raise ViewContractCompatibilityError(issues)
    return NegotiatedViewContract(
        renderer_id=renderer.renderer_id,
        schema_version=document.schema_version,
        document=document,
    )


def _components(component: ViewComponent | None, path: str):
    if component is None:
        return
    yield path, component
    for index, child in enumerate(component.children):
        yield from _components(child, f"{path}.children[{index}]")
