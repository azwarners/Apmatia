from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    SUPPORTED_COMPONENT_TYPES,
    SUPPORTED_ACTION_SCOPES,
    SUPPORTED_CONDITION_OPERATORS,
    SUPPORTED_DATA_SOURCE_KINDS,
    SUPPORTED_EFFECT_TYPES,
    SUPPORTED_FIELD_TYPES,
    SUPPORTED_REFRESH_MODES,
    SUPPORTED_STATE_SCOPES,
    SUPPORTED_STATE_VALUE_TYPES,
    SUPPORTED_UPDATE_STRATEGIES,
    VIEW_CONTRACT_VERSION,
    ViewBinding,
    ViewComponent,
    ViewCondition,
    ViewDocument,
    ViewEffect,
)


@dataclass(frozen=True, slots=True)
class ViewContractIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ViewContractValidationError(ValueError):
    def __init__(self, issues: list[ViewContractIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("Invalid view document: " + "; ".join(str(issue) for issue in issues))


def validate_view_document(document: ViewDocument) -> ViewDocument:
    issues: list[ViewContractIssue] = []
    root = f"views[{document.view_id or '?'}]"
    _required(document.view_id, f"{root}.view_id", issues)
    _required(document.module_id, f"{root}.module_id", issues)
    _required(document.title, f"{root}.title", issues)
    if document.schema_version != VIEW_CONTRACT_VERSION:
        issues.append(
            ViewContractIssue(
                f"{root}.schema_version",
                f"unsupported version {document.schema_version}; expected {VIEW_CONTRACT_VERSION}",
            )
        )

    source_keys = _unique_keys(document.data_sources, "key", f"{root}.data_sources", issues)
    state_keys = _unique_keys(document.state, "key", f"{root}.state", issues)
    action_keys = _unique_keys(document.actions, "key", f"{root}.actions", issues)

    for index, source in enumerate(document.data_sources):
        path = f"{root}.data_sources[{index}]"
        if source.kind not in SUPPORTED_DATA_SOURCE_KINDS:
            issues.append(ViewContractIssue(f"{path}.kind", f"unsupported data-source kind: {source.kind}"))
        if not source.operation:
            issues.append(ViewContractIssue(f"{path}.operation", "data source operation cannot be empty"))
        for dependency_index, dependency in enumerate(source.depends_on):
            if dependency not in source_keys and dependency not in state_keys:
                issues.append(
                    ViewContractIssue(
                        f"{path}.depends_on[{dependency_index}]",
                        f"unknown data source or state key: {dependency}",
                    )
                )
        _validate_nested_bindings(source.parameters, f"{path}.parameters", source_keys, state_keys, issues)
        _validate_refresh(source.refresh, f"{path}.refresh", source_keys, state_keys, issues)
    for index, state in enumerate(document.state):
        if state.scope not in SUPPORTED_STATE_SCOPES:
            issues.append(
                ViewContractIssue(f"{root}.state[{index}].scope", f"unsupported state scope: {state.scope}")
            )
        if state.value_type not in SUPPORTED_STATE_VALUE_TYPES:
            issues.append(
                ViewContractIssue(
                    f"{root}.state[{index}].value_type",
                    f"unsupported state value type: {state.value_type}",
                )
            )
    for index, action in enumerate(document.actions):
        path = f"{root}.actions[{index}]"
        _required(action.intent, f"{path}.intent", issues)
        _required(action.label, f"{path}.label", issues)
        if action.scope not in SUPPORTED_ACTION_SCOPES:
            issues.append(ViewContractIssue(f"{path}.scope", f"unsupported action scope: {action.scope}"))
        if not action.command_id and not action.operation:
            issues.append(ViewContractIssue(path, "action must declare command_id or operation"))
        _validate_nested_bindings(action.payload, f"{path}.payload", source_keys, state_keys, issues)
        _validate_condition(action.enabled_when, f"{path}.enabled_when", source_keys, state_keys, issues)
        for effect_index, effect in enumerate((*action.success_effects, *action.failure_effects)):
            _validate_effect(effect, f"{path}.effects[{effect_index}]", source_keys, state_keys, issues)
    for index, effect in enumerate(document.effects):
        _validate_effect(effect, f"{root}.effects[{index}]", source_keys, state_keys, issues)
    _validate_refresh(document.refresh_policy, f"{root}.refresh_policy", source_keys, state_keys, issues)

    component_ids: set[str] = set()
    if document.presentation is None:
        issues.append(ViewContractIssue(f"{root}.presentation", "presentation is required"))
    else:
        if document.presentation.component_type != "page":
            issues.append(ViewContractIssue(f"{root}.presentation.component_type", "root component must be page"))
        _validate_component(
            document.presentation,
            f"{root}.presentation",
            component_ids,
            source_keys,
            state_keys,
            action_keys,
            issues,
        )

    if issues:
        raise ViewContractValidationError(issues)
    return document


def _validate_component(
    component: ViewComponent,
    path: str,
    component_ids: set[str],
    source_keys: set[str],
    state_keys: set[str],
    action_keys: set[str],
    issues: list[ViewContractIssue],
) -> None:
    if not component.component_id:
        issues.append(ViewContractIssue(f"{path}.component_id", "component ID cannot be empty"))
    elif component.component_id in component_ids:
        issues.append(ViewContractIssue(f"{path}.component_id", f"duplicate component ID: {component.component_id}"))
    else:
        component_ids.add(component.component_id)
    if component.component_type not in SUPPORTED_COMPONENT_TYPES:
        issues.append(
            ViewContractIssue(f"{path}.component_type", f"unsupported component type: {component.component_type}")
        )
    if component.binding is not None:
        if component.binding.source not in source_keys and component.binding.source not in state_keys:
            issues.append(
                ViewContractIssue(
                    f"{path}.binding.source",
                    f"unknown data source or state key: {component.binding.source}",
                )
            )
    elif component.component_type in {"collection", "table", "timeline", "tree"}:
        issues.append(ViewContractIssue(f"{path}.binding", f"{component.component_type} component requires a binding"))
    for index, action_key in enumerate(component.action_keys):
        if action_key not in action_keys:
            issues.append(ViewContractIssue(f"{path}.action_keys[{index}]", f"unknown action key: {action_key}"))
    if component.component_type == "field" and not str(component.properties.get("key") or "").strip():
        issues.append(ViewContractIssue(f"{path}.properties.key", "field component requires a key"))
    if component.component_type == "field":
        field_type = str(component.properties.get("field_type") or "text")
        if field_type not in SUPPORTED_FIELD_TYPES:
            issues.append(ViewContractIssue(f"{path}.properties.field_type", f"unsupported field type: {field_type}"))
    _validate_nested_bindings(component.properties, f"{path}.properties", source_keys, state_keys, issues)
    _validate_condition(component.visible_when, f"{path}.visible_when", source_keys, state_keys, issues)
    for index, child in enumerate(component.children):
        _validate_component(
            child,
            f"{path}.children[{index}]",
            component_ids,
            source_keys,
            state_keys,
            action_keys,
            issues,
        )


def _validate_condition(
    condition: ViewCondition | None,
    path: str,
    source_keys: set[str],
    state_keys: set[str],
    issues: list[ViewContractIssue],
) -> None:
    if condition is None:
        return
    if condition.operator not in SUPPORTED_CONDITION_OPERATORS:
        issues.append(ViewContractIssue(f"{path}.operator", f"unsupported condition operator: {condition.operator}"))
    operand_count = len(condition.operands)
    if condition.operator in {"not", "exists", "truthy", "falsy"} and operand_count != 1:
        issues.append(ViewContractIssue(f"{path}.operands", f"{condition.operator} requires exactly one operand"))
    if condition.operator in {"equals", "not_equals", "in", "not_in", "gt", "gte", "lt", "lte"} and operand_count != 2:
        issues.append(ViewContractIssue(f"{path}.operands", f"{condition.operator} requires exactly two operands"))
    if condition.operator in {"all", "any"} and operand_count < 1:
        issues.append(ViewContractIssue(f"{path}.operands", f"{condition.operator} requires at least one operand"))
    for index, operand in enumerate(condition.operands):
        if isinstance(operand, ViewCondition):
            _validate_condition(operand, f"{path}.operands[{index}]", source_keys, state_keys, issues)
        elif isinstance(operand, ViewBinding):
            if operand.source not in source_keys and operand.source not in state_keys and operand.source != "capabilities":
                issues.append(
                    ViewContractIssue(f"{path}.operands[{index}].source", f"unknown binding source: {operand.source}")
                )


def _validate_effect(
    effect: ViewEffect,
    path: str,
    source_keys: set[str],
    state_keys: set[str],
    issues: list[ViewContractIssue],
) -> None:
    if effect.effect_type not in SUPPORTED_EFFECT_TYPES:
        issues.append(ViewContractIssue(f"{path}.effect_type", f"unsupported effect: {effect.effect_type}"))
    if effect.effect_type in {"refresh_source", "start_polling", "stop_polling"} and effect.target not in source_keys:
        issues.append(ViewContractIssue(f"{path}.target", f"unknown data source: {effect.target}"))
    if effect.effect_type in {"set_state", "clear_state", "select_item"} and effect.target not in state_keys:
        issues.append(ViewContractIssue(f"{path}.target", f"unknown state key: {effect.target}"))
    if effect.effect_type == "navigate" and not effect.target:
        issues.append(ViewContractIssue(f"{path}.target", "navigate effect requires a target view ID"))


def _validate_refresh(policy, path: str, source_keys: set[str], state_keys: set[str], issues: list[ViewContractIssue]) -> None:
    if policy.mode not in SUPPORTED_REFRESH_MODES:
        issues.append(ViewContractIssue(f"{path}.mode", f"unsupported refresh mode: {policy.mode}"))
    if policy.update_strategy not in SUPPORTED_UPDATE_STRATEGIES:
        issues.append(
            ViewContractIssue(f"{path}.update_strategy", f"unsupported update strategy: {policy.update_strategy}")
        )
    if policy.mode == "poll" and (policy.interval_seconds is None or policy.interval_seconds <= 0):
        issues.append(ViewContractIssue(f"{path}.interval_seconds", "poll refresh requires a positive interval"))
    _validate_condition(policy.stop_when, f"{path}.stop_when", source_keys, state_keys, issues)


def _unique_keys(items: tuple[Any, ...], attribute: str, path: str, issues: list[ViewContractIssue]) -> set[str]:
    keys: set[str] = set()
    for index, item in enumerate(items):
        key = str(getattr(item, attribute, "") or "").strip()
        if not key:
            issues.append(ViewContractIssue(f"{path}[{index}].{attribute}", f"{attribute} cannot be empty"))
        elif key in keys:
            issues.append(ViewContractIssue(f"{path}[{index}].{attribute}", f"duplicate {attribute}: {key}"))
        else:
            keys.add(key)
    return keys


def _required(value: str, path: str, issues: list[ViewContractIssue]) -> None:
    if not str(value or "").strip():
        issues.append(ViewContractIssue(path, "value cannot be empty"))


def _validate_nested_bindings(
    value: Any,
    path: str,
    source_keys: set[str],
    state_keys: set[str],
    issues: list[ViewContractIssue],
) -> None:
    if isinstance(value, ViewBinding):
        if value.source not in source_keys and value.source not in state_keys and value.source != "capabilities":
            issues.append(ViewContractIssue(f"{path}.source", f"unknown binding source: {value.source}"))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_nested_bindings(item, f"{path}.{key}", source_keys, state_keys, issues)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_nested_bindings(item, f"{path}[{index}]", source_keys, state_keys, issues)
