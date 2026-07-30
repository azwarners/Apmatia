# View Extraction Phase 0 Baseline

## Purpose

Phase 0 freezes the current interface coupling before extraction begins. The baseline does not
approve the existing coupling as good architecture. It makes that debt explicit and prevents it
from growing while later phases remove it.

The executable baseline lives in:

- `tests/unit/test_interface_view_architecture.py`
- `tests/unit/test_view_extraction_parity_baseline.py`
- `tests/unit/test_streamlit_discussion_baseline.py`

## Frozen Architecture Debt

The architecture test inventories:

- literal module and view identifiers used in Streamlit comparisons
- the `agents`, `users`, and `preferences` renderer escape hatches
- handwritten Streamlit module screens
- files allowed under the Streamlit `pages` package
- direct interface imports from core and module implementation packages
- GUI-framework imports from module packages

All inventories are exact allowlists. A new entry fails tests. Removing an existing entry is
expected as migration proceeds and requires deleting it from the corresponding allowlist.

The current custom-screen allowlist is:

- Agents
- Discussion
- Preferences Module Management
- Users and Groups

The current renderer-token allowlist is:

- `agents`
- `preferences`
- `users`

No fourth token or custom screen may be introduced.

## Portable-Metadata Requirement

New module UI work must register a view and use the framework-neutral contract or legacy metadata
accepted by the validated compatibility normalizer. It must not add:

- a Streamlit page
- a handwritten Streamlit module renderer
- a renderer token
- a literal module/view dispatch branch
- a direct import from an interface to module implementation code

Registry registration validates the normalized document, while the Phase 0 architecture tests
prevent new interface escape hatches.

## Behavioral Parity Baseline

The parity inventory references real, executable tests for:

- generic collection, form, create, edit, and delete behavior
- Agent Config, alarms, host SSH preparation, and dynamic options
- agent create, edit, clone, and delete behavior
- user, group, and membership behavior
- module activation, visibility, and ordering behavior
- Discussion, messages, participants, and contacts-shell behavior
- Agent Loops shell, task launch/stop, progress, history, and live output behavior

Each referenced test is verified by AST. Deleting or renaming a baseline test fails Phase 0 unless a
later migration phase explicitly replaces it with an equivalent renderer-neutral parity test.

## Change Procedure

During extraction:

1. Remove migrated debt from an allowlist; do not replace it with a new exception.
2. Retain the associated parity tests until the new path passes equivalent assertions.
3. When a renderer-neutral test supersedes an old Streamlit test, update the parity reference in
   the same change.
4. Never expand an allowlist merely to make a new custom screen pass.

## Completion Gate

Phase 0 is complete when these exact inventories and behavioral references pass in the full test
suite. Later phases progressively drive the allowlists toward empty sets.
