"""Framework-free headless renderer/validator for view contract documents.

This module walks every component, source, binding, condition, state definition, action payload,
navigation target, effect, and refresh policy in a view document without importing any interface
package. It reports precise contract paths for missing or unsupported behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    SUPPORTED_ACTION_SCOPES,
    SUPPORTED_COMPONENT_TYPES,
    SUPPORTED_CONDITION_OPERATORS,
    SUPPORTED_DATA_SOURCE_KINDS,
    SUPPORTED_EFFECT_TYPES,
    SUPPORTED_FIELD_TYPES,
    SUPPORTED_REFRESH_MODES,
    SUPPORTED_STATE_SCOPES,
    SUPPORTED_STATE_VALUE_TYPES,
    SUPPORTED_UPDATE_STRATEGIES,
    ViewAction,
    ViewBinding,
    ViewComponent,
    ViewCondition,
    ViewDataSource,
    ViewDocument,
    ViewEffect,
    ViewStateDefinition,
    VIEW_CONTRACT_VERSION,
)
from .validation import ViewContractIssue


@dataclass(frozen=True, slots=True)
class HeadlessRenderResult:
    """Result of a headless render/validation pass."""

    view_id: str
    module_id: str
    title: str
    supported: bool
    issues: tuple[HeadlessIssue, ...] = field(default_factory=tuple)
    rendered_components: int = 0
    resolved_data_sources: int = 0
    resolved_actions: int = 0
    resolved_effects: int = 0


@dataclass(frozen=True, slots=True)
class HeadlessIssue:
    """A single issue discovered during headless rendering."""

    path: str
    issue_type: str
    message: str


def render_view_document_headless(
    document: ViewDocument,
    *,
    data_source_values: dict[str, Any] | None = None,
    state_values: dict[str, Any] | None = None,
    capabilities: frozenset[str] = frozenset(),
) -> HeadlessRenderResult:
    """Render a view document without any framework.

    Args:
        document: The view document to render.
        data_source_values: Optional pre-resolved data source values keyed by source key.
        state_values: Optional pre-resolved state values keyed by state key.
        capabilities: Optional set of capability IDs the renderer supports.

    Returns:
        A HeadlessRenderResult with issues, component counts, and support status.
    """
    issues: list[HeadlessIssue] = []
    data_source_values = data_source_values or {}
    state_values = state_values or {}

    # Validate schema version
    if document.schema_version != VIEW_CONTRACT_VERSION:
        issues.append(
            HeadlessIssue(
                f"views[{document.view_id}].schema_version",
                "unsupported_version",
                f"expected {VIEW_CONTRACT_VERSION}, got {document.schema_version}",
            )
        )

    # Validate data sources
    resolved_sources = _resolve_data_sources(document, data_source_values, capabilities, issues)
    resolved_state = _resolve_state_definitions(document, state_values, resolved_sources, issues)

    # Validate actions
    resolved_actions = _resolve_actions(document, resolved_sources, resolved_state, capabilities, issues)

    # Validate effects
    resolved_effects = _resolve_effects(document, resolved_sources, resolved_state, issues)

    # Validate presentation
    rendered_components = 0
    if document.presentation is None:
        issues.append(
            HeadlessIssue(
                f"views[{document.view_id}].presentation",
                "missing_component",
                "presentation is required",
            )
        )
    else:
        rendered_components = _walk_component_tree(
            document.presentation,
            document.view_id,
            resolved_sources,
            resolved_state,
            resolved_actions,
            capabilities,
            issues,
        )

    # Validate refresh policy
    _validate_refresh_policy(document.refresh_policy, f"views[{document.view_id}].refresh_policy", resolved_sources, resolved_state, issues)

    supported = len(issues) == 0
    return HeadlessRenderResult(
        view_id=document.view_id,
        module_id=document.module_id,
        title=document.title,
        supported=supported,
        issues=tuple(issues),
        rendered_components=rendered_components,
        resolved_data_sources=len(resolved_sources),
        resolved_actions=len(resolved_actions),
        resolved_effects=len(resolved_effects),
    )


def _resolve_data_sources(
    document: ViewDocument,
    preloaded: dict[str, Any],
    capabilities: frozenset[str],
    issues: list[HeadlessIssue],
) -> dict[str, Any]:
    """Resolve data sources for a view document."""
    resolved: dict[str, Any] = {}

    for source in document.data_sources:
        path = f"views[{document.view_id}].data_sources[{source.key}]"

        if source.kind not in SUPPORTED_DATA_SOURCE_KINDS:
            issues.append(
                HeadlessIssue(
                    f"{path}.kind",
                    "unsupported_data_source_kind",
                    f"expected one of {SUPPORTED_DATA_SOURCE_KINDS}, got {source.kind}",
                )
            )

        if not source.operation:
            issues.append(
                HeadlessIssue(
                    f"{path}.operation",
                    "missing_operation",
                    "operation cannot be empty",
                )
            )

        # Check dependencies
        for dep in source.depends_on:
            if dep not in preloaded:
                issues.append(
                    HeadlessIssue(
                        f"{path}.depends_on[{dep}]",
                        "unknown_dependency",
                        f"data source or state key not found: {dep}",
                    )
                )

        # Use preloaded value if available, otherwise mark as unresolved
        if source.key in preloaded:
            resolved[source.key] = preloaded[source.key]
        else:
            resolved[source.key] = None
            issues.append(
                HeadlessIssue(
                    f"{path}",
                    "unresolved_data_source",
                    f"no value provided for data source '{source.key}' (operation: {source.operation})",
                )
            )

    return resolved


def _resolve_state_definitions(
    document: ViewDocument,
    preloaded: dict[str, Any],
    sources: dict[str, Any],
    issues: list[HeadlessIssue],
) -> dict[str, Any]:
    """Resolve state definitions for a view document."""
    resolved: dict[str, Any] = {}

    for state in document.state:
        path = f"views[{document.view_id}].state[{state.key}]"

        if state.scope not in SUPPORTED_STATE_SCOPES:
            issues.append(
                HeadlessIssue(
                    f"{path}.scope",
                    "unsupported_state_scope",
                    f"expected one of {SUPPORTED_STATE_SCOPES}, got {state.scope}",
                )
            )

        if state.value_type not in SUPPORTED_STATE_VALUE_TYPES:
            issues.append(
                HeadlessIssue(
                    f"{path}.value_type",
                    "unsupported_state_value_type",
                    f"expected one of {SUPPORTED_STATE_VALUE_TYPES}, got {state.value_type}",
                )
            )

        resolved[state.key] = preloaded.get(state.key, state.default)

    return resolved


def _resolve_actions(
    document: ViewDocument,
    sources: dict[str, Any],
    state: dict[str, Any],
    capabilities: frozenset[str],
    issues: list[HeadlessIssue],
) -> dict[str, ViewAction]:
    """Resolve actions for a view document."""
    resolved: dict[str, ViewAction] = {}

    for action in document.actions:
        path = f"views[{document.view_id}].actions[{action.key}]"

        if action.scope not in SUPPORTED_ACTION_SCOPES:
            issues.append(
                HeadlessIssue(
                    f"{path}.scope",
                    "unsupported_action_scope",
                    f"expected one of {SUPPORTED_ACTION_SCOPES}, got {action.scope}",
                )
            )

        if not action.command_id and not action.operation:
            issues.append(
                HeadlessIssue(
                    path,
                    "missing_intent_target",
                    "action must declare command_id or operation",
                )
            )

        # Check enabled condition
        if action.enabled_when is not None:
            if not _evaluate_condition(action.enabled_when, sources, state, capabilities):
                resolved[action.key] = action  # Action is disabled
                continue

        # Check effects reference valid targets
        for effect in (*action.success_effects, *action.failure_effects):
            if effect.effect_type in {"refresh_source", "start_polling", "stop_polling"}:
                if effect.target not in sources:
                    issues.append(
                        HeadlessIssue(
                            f"{path}.effects[{effect.effect_type}].target",
                            "unknown_effect_target",
                            f"unknown data source: {effect.target}",
                        )
                    )
            elif effect.effect_type in {"set_state", "clear_state", "select_item"}:
                if effect.target not in state:
                    issues.append(
                        HeadlessIssue(
                            f"{path}.effects[{effect.effect_type}].target",
                            "unknown_effect_target",
                            f"unknown state key: {effect.target}",
                        )
                    )
            elif effect.effect_type == "navigate" and not effect.target:
                issues.append(
                    HeadlessIssue(
                        f"{path}.effects[{effect.effect_type}].target",
                        "missing_navigate_target",
                        "navigate effect requires a target view ID",
                    )
                )

        resolved[action.key] = action

    return resolved


def _resolve_effects(
    document: ViewDocument,
    sources: dict[str, Any],
    state: dict[str, Any],
    issues: list[HeadlessIssue],
) -> dict[str, ViewEffect]:
    """Resolve document-level effects."""
    resolved: dict[str, ViewEffect] = {}

    for effect in document.effects:
        path = f"views[{document.view_id}].effects[{effect.effect_type}]"

        if effect.effect_type not in SUPPORTED_EFFECT_TYPES:
            issues.append(
                HeadlessIssue(
                    f"{path}.effect_type",
                    "unsupported_effect_type",
                    f"expected one of {SUPPORTED_EFFECT_TYPES}, got {effect.effect_type}",
                )
            )
            continue

        if effect.effect_type in {"refresh_source", "start_polling", "stop_polling"}:
            if effect.target not in sources:
                issues.append(
                    HeadlessIssue(
                        f"{path}.target",
                        "unknown_effect_target",
                        f"unknown data source: {effect.target}",
                    )
                )
        elif effect.effect_type in {"set_state", "clear_state", "select_item"}:
            if effect.target not in state:
                issues.append(
                    HeadlessIssue(
                        f"{path}.target",
                        "unknown_effect_target",
                        f"unknown state key: {effect.target}",
                    )
                )
        elif effect.effect_type == "navigate" and not effect.target:
            issues.append(
                HeadlessIssue(
                    f"{path}.target",
                    "missing_navigate_target",
                    "navigate effect requires a target view ID",
                )
            )

        resolved[f"{effect.effect_type}:{effect.target or ''}"] = effect

    return resolved


def _walk_component_tree(
    component: ViewComponent,
    view_id: str,
    sources: dict[str, Any],
    state: dict[str, Any],
    actions: dict[str, ViewAction],
    capabilities: frozenset[str],
    issues: list[HeadlessIssue],
) -> int:
    """Walk the component tree and count rendered components."""
    count = 1
    path = f"views[{view_id}].presentation"

    # Validate component type
    if component.component_type not in SUPPORTED_COMPONENT_TYPES:
        issues.append(
            HeadlessIssue(
                f"{path}.component_type",
                "unsupported_component_type",
                f"expected one of {SUPPORTED_COMPONENT_TYPES}, got {component.component_type}",
            )
        )

    # Validate binding
    if component.binding is not None:
        if component.binding.source not in sources and component.binding.source not in state:
            issues.append(
                HeadlessIssue(
                    f"{path}.binding.source",
                    "unknown_binding_source",
                    f"unknown data source or state key: {component.binding.source}",
                )
            )

    # Validate action keys
    for index, action_key in enumerate(component.action_keys):
        if action_key not in actions:
            issues.append(
                HeadlessIssue(
                    f"{path}.action_keys[{index}]",
                    "unknown_action_key",
                    f"unknown action key: {action_key}",
                )
            )

    # Validate visible condition
    if component.visible_when is not None:
        if not _evaluate_condition(component.visible_when, sources, state, capabilities):
            count = 0  # Component is not rendered

    # Validate field-specific properties
    if component.component_type == "field":
        field_type = str(component.properties.get("field_type") or "text")
        if field_type not in SUPPORTED_FIELD_TYPES:
            issues.append(
                HeadlessIssue(
                    f"{path}.properties.field_type",
                    "unsupported_field_type",
                    f"expected one of {SUPPORTED_FIELD_TYPES}, got {field_type}",
                )
            )

    # Recurse into children
    for index, child in enumerate(component.children):
        count += _walk_component_tree(
            child,
            view_id,
            sources,
            state,
            actions,
            capabilities,
            issues,
        )

    return count


def _evaluate_condition(
    condition: ViewCondition,
    sources: dict[str, Any],
    state: dict[str, Any],
    capabilities: frozenset[str],
) -> bool:
    """Evaluate a condition against sources, state, and capabilities."""
    operator = condition.operator

    if operator == "all":
        return all(_evaluate_condition(op, sources, state, capabilities) for op in condition.operands)
    elif operator == "any":
        return any(_evaluate_condition(op, sources, state, capabilities) for op in condition.operands)
    elif operator == "not":
        return not _evaluate_condition(condition.operands[0], sources, state, capabilities)
    elif operator == "equals":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left == right
    elif operator == "not_equals":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left != right
    elif operator == "in":
        value = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        collection = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return value in collection if isinstance(collection, (list, tuple, set)) else False
    elif operator == "not_in":
        value = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        collection = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return value not in collection if isinstance(collection, (list, tuple, set)) else False
    elif operator == "exists":
        binding = condition.operands[0]
        if isinstance(binding, ViewBinding):
            return binding.source in sources or binding.source in state
        return True
    elif operator == "truthy":
        value = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        return bool(value)
    elif operator == "falsy":
        value = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        return not bool(value)
    elif operator == "gt":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left > right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
    elif operator == "gte":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left >= right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
    elif operator == "lt":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left < right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False
    elif operator == "lte":
        left = _resolve_binding_value(condition.operands[0], sources, state, capabilities)
        right = _resolve_binding_value(condition.operands[1], sources, state, capabilities)
        return left <= right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else False

    return True


def _resolve_binding_value(
    binding_or_value: ViewBinding | Any,
    sources: dict[str, Any],
    state: dict[str, Any],
    capabilities: frozenset[str],
) -> Any:
    """Resolve a binding or literal value."""
    if isinstance(binding_or_value, ViewBinding):
        source = binding_or_value.source
        if source == "capabilities":
            return capabilities
        if source in sources:
            value = sources[source]
        elif source in state:
            value = state[source]
        else:
            value = binding_or_value.default
        # Apply path if present
        if binding_or_value.path and isinstance(value, dict):
            for key in binding_or_value.path.split("."):
                value = value.get(key) if isinstance(value, dict) else value
            return value
        return value
    return binding_or_value


def _validate_refresh_policy(
    policy,
    path: str,
    sources: dict[str, Any],
    state: dict[str, Any],
    issues: list[HeadlessIssue],
) -> None:
    """Validate a refresh policy."""
    if policy.mode not in SUPPORTED_REFRESH_MODES:
        issues.append(
            HeadlessIssue(
                f"{path}.mode",
                "unsupported_refresh_mode",
                f"expected one of {SUPPORTED_REFRESH_MODES}, got {policy.mode}",
            )
        )

    if policy.update_strategy not in SUPPORTED_UPDATE_STRATEGIES:
        issues.append(
            HeadlessIssue(
                f"{path}.update_strategy",
                "unsupported_update_strategy",
                f"expected one of {SUPPORTED_UPDATE_STRATEGIES}, got {policy.update_strategy}",
            )
        )

    if policy.mode == "poll" and (policy.interval_seconds is None or policy.interval_seconds <= 0):
        issues.append(
            HeadlessIssue(
                f"{path}.interval_seconds",
                "invalid_poll_interval",
                "poll refresh requires a positive interval",
            )
        )

    if policy.stop_when is not None:
        if not _evaluate_condition(policy.stop_when, sources, state, frozenset()):
            pass  # Stop condition is met