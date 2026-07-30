# Framework-Neutral View Contract Version 1

## Purpose

This document defines the renderer-independent view contract owned by
`src/apmatia/core/view_contract/`. Module view specifications and API responses use this contract;
Streamlit and future interfaces consume it.

Contract version 1 is intentionally capable of describing both ordinary collection/form views and
the richer Discussion and Agent Loops experiences. A renderer must negotiate support before
rendering a document.

## Ownership Boundary

- Modules own view semantics and module-specific specifications.
- Module view providers own view-model assembly and capability calculation.
- Core owns contract models, normalization, validation, and compatibility negotiation.
- APIs serialize documents and view models.
- Renderers own toolkit widgets, local widget identities, styling, and framework event mechanics.

No contract type imports an interface package or GUI framework.

## Document Shape

`ViewDocument` contains:

| Field | Meaning |
|---|---|
| `schema_version` | Contract version; version 1 is currently supported |
| `view_id` | Stable registry view identifier |
| `module_id` | Owning module identifier |
| `title` | Primary display title |
| `description` | View purpose |
| `presentation` | Root semantic component; it must be a `page` |
| `data_sources` | API-accessible singleton, collection, stream, or tree data |
| `state` | Typed semantic state independent of widget keys |
| `actions` | User intents and their operations, conditions, and effects |
| `effects` | View-level effects |
| `refresh_policy` | Default refresh behavior |
| `capabilities` | Domain capabilities referenced by conditions |
| `required_renderer_capabilities` | Non-component renderer features required by the view |
| `metadata` | Compatibility or non-semantic diagnostic metadata |

Documents are immutable dataclasses and `to_dict()` returns JSON-safe data. Dates and times use ISO
8601 strings, enums use their values, paths use strings, and tuples become arrays.

## Semantic Components

Version 1 supports:

- structure: `page`, `stack`, `columns`, `tabs`, `panel`, `card`, `expander`
- data display: `collection`, `table`, `detail`, `tree`
- input: `form`, `field`, `composer`
- content: `text`, `markdown`, `notice`, `status`
- actions and navigation: `actions`, `navigation`
- live and rich output: `timeline`, `message`, `terminal`, `progress`, `checklist`

Every component has a stable `component_id`, semantic `component_type`, optional properties,
optional binding, optional visibility condition, referenced action keys, and child components.
Component IDs must be unique within a document. Collection, table, timeline, and tree components
must bind to a declared data source or state key.

Component properties are semantic hints, not framework calls. Properties must never contain
Streamlit keys, CSS selectors, rerun instructions, or framework widget objects.

## Fields

Portable field types are:

- `text`
- `textarea`
- `number`
- `checkbox`
- `color`
- `slider`
- `select`
- `multiselect`
- `date`
- `time`
- `datetime`
- `password`
- `hidden`
- `file`

Renderers negotiate field-type support separately from component support. Dynamic options should be
provided through `ViewBinding` values or view-model data rather than patched into a framework form.

## Bindings

`ViewBinding` identifies a declared data source, semantic state key, or the reserved
`capabilities` source. Its `path` selects nested data and its `default` supplies a missing-value
fallback.

Validation checks bindings in:

- component bindings
- component properties
- data-source parameters
- action payloads
- conditions

Bindings cannot import Python callables or contain executable expressions.

## Data Sources

`ViewDataSource` declares:

- stable `key`
- `kind`: `singleton`, `collection`, `stream`, or `tree`
- API or module-view `operation`
- bound parameters
- dependencies on state or other sources
- optional projection
- item identity
- loading, empty, and error text
- refresh policy

Every source must declare an operation. Dependencies must resolve to another source or state key.

## State

State scopes are:

- `event`: one intent dispatch
- `view`: current view instance
- `session`: navigation within the authenticated session
- `server`: persisted or authoritative server state

Value types are `string`, `integer`, `number`, `boolean`, `date`, `time`, `datetime`, `object`, and
`array`. Semantic state keys are not renderer widget IDs.

## Conditions

Conditions use a closed operator set:

- logical: `all`, `any`, `not`
- equality and membership: `equals`, `not_equals`, `in`, `not_in`
- presence and truth: `exists`, `truthy`, `falsy`
- ordering: `gt`, `gte`, `lt`, `lte`

`not`, `exists`, `truthy`, and `falsy` take one operand. Comparisons and membership operators take
two. `all` and `any` take at least one. Operands may nest conditions, use bindings, or contain
JSON-safe constants. Arbitrary Python evaluation is prohibited.

## Actions and Effects

Action scopes are `view`, `item`, `selection`, `form`, `message`, and `navigation`. Each action must
declare a command ID or API operation. It may declare payload bindings, confirmation, duplicate
submission prevention, an enabled condition, and success/failure effects.

Effects are:

- `refresh_source`
- `refresh_view`
- `set_state`
- `clear_state`
- `select_item`
- `navigate`
- `open_panel`
- `close_panel`
- `show_notification`
- `start_polling`
- `stop_polling`
- `download`

Source effects must target declared data sources. State effects must target declared state.
Navigation effects require a stable target view ID. Renderers decide how these effects map to their
routing and event systems.

## Live Updates

Refresh modes are `manual`, `on_intent`, `poll`, and `stream`. Policies define:

- positive polling interval when mode is `poll`
- cursor key
- generation key
- `append` or `replace` update strategy
- stale-response rejection
- an optional stop condition

Discussion is modeled with append-style message streaming plus a generation token and a polled
activity singleton. Agent Loops is modeled with replace-style task polling, a generation token, and
a status-based stop condition. These representative contracts are enforced in
`tests/unit/test_view_contract_rich_views.py`.

## Renderer Negotiation

Before rendering, call `negotiate_view_contract(document, renderer_capabilities)`.

A renderer declares:

- renderer ID
- supported contract versions
- component types
- field types
- effect types
- data-source kinds
- additional renderer capabilities such as `stream_updates`, `file_input`, `polling`, or
  `terminal_output`

Negotiation returns `NegotiatedViewContract` only when every requirement is supported. Otherwise it
raises `ViewContractCompatibilityError` with paths identifying the unsupported version, component,
field type, effect, data source, or capability. Unsupported features must never disappear silently.

Core validation currently implements contract version 1. A future document version is rejected
with an explicit version path. Supporting another version requires new validation and an explicit
renderer declaration; version numbers are never coerced.

## Legacy Compatibility Inventory

The compatibility normalizer accepts the following historical Streamlit-adapter fields. This list
is canonical in `LEGACY_ADAPTER_FIELD_INVENTORY` and protected by a literal regression test.

| Context | Accepted fields |
|---|---|
| View | `module_id`, `view_id`, `name`, `description`, `metadata` |
| Metadata | `ui`, `plural_label`, `singular_label`, `empty_state`, `schema`, `commands`, `view_contract` |
| Portable contract extension | `data_sources`, `field_option_sources` |
| Portable data source | `key`, `kind`, `operation`, `parameters`, `depends_on`, `projection`, `item_key`, `loading_text`, `empty_text`, `error_text` |
| UI | `render_mode`, `layout`, `renderer`, `title`, `caption`, `empty_state`, `item_key`, `columns`, `fields`, `item_actions`, `view_actions`, `commands`, `create_form`, `edit_form`, `form`, `nav_pane` |
| Column | `key`, `source`, `label`, `empty_value` |
| Action | `key`, `intent`, `label`, `scope`, `style`, `confirmation`, `payload` |
| Form | `key`, `title`, `description`, `submit_label`, `cancel_label`, `actions`, `fields` |
| Form action | `key`, `intent`, `label`, `style`, `payload` |
| Field | `key`, `label`, `section`, `field_type`, `type`, `input`, `help_text`, `help`, `placeholder`, `default`, `required`, `min_value`, `max_value`, `step`, `options`, `list`, `create`, `edit`, `empty_value` |
| Navigation pane | `title`, `top_exit_label`, `bottom_exit_label`, `empty_state`, `item_label_key`, `item_subtitle_key`, `item_detail_key`, `item_value_key` |
| Schema | `version`, `fields`, `create`, `edit`, `resources` |
| Schema section | `key`, `title`, `description`, `submit_label`, `cancel_label`, `actions`, `fields`, `extra_fields` |
| Commands | `list`, `create`, `edit`, `delete` |

`layout` and `renderer` are retained only as diagnostic legacy metadata. They do not provide
portable semantics and must not be added to new module specifications. The compatibility inventory
is frozen except for the `view_contract` bridge used while registry contributions remain
`ViewContribution` metadata. That bridge is normalized immediately into typed `ViewDataSource` and
`ViewBinding` values; renderers consume only the serialized versioned document.

## Validation Lifecycle

Registry view registration normalizes and validates the compatibility document before storing the
view. Direct typed documents call `validate_view_document()`. Errors include actionable paths such
as:

```text
views[discuss.conversation.view].presentation.children[1].binding.source
```

Validation covers identifiers, versions, unique keys, component IDs and types, field types,
bindings, source dependencies, state types/scopes, action scopes and operations, conditions,
effects, refresh policies, and JSON serialization.

## Version 1 Completion Evidence

Contract version 1 is considered foundationally complete because:

1. The historical adapter input surface is inventoried and regression-tested.
2. Neutral models cover collections, forms, actions, state, conditions, data, navigation, effects,
   rich output, and live refresh.
3. Representative Discussion and Agent Loops documents validate and negotiate successfully.
4. Legacy metadata remains compatible through a neutral normalizer.
5. Registry registration validates normalized documents.
6. Validation errors identify exact document paths.
7. Renderer version and feature incompatibilities are explicit.
8. Documents serialize and import without Streamlit.
9. Authenticated HTTP clients can discover all active documents at `GET /api/module-view-documents`
   and retrieve one document at `GET /api/module-views/{view_id}/document`.
10. Every bundled registered view, including development-module views, has a deterministic
    full-document snapshot generated with Streamlit imports blocked.

Public authentication documents use the same contract at `GET /api/auth/views`; this endpoint is
intentionally available before login. Authenticated document discovery remains available through
the general catalog and individual-document endpoints.

This completion does not mean module-specific extraction is finished. It means the stable contract
needed by later workstreams is available without adding new custom-renderer escape hatches.
