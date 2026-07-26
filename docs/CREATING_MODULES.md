# Creating Modules

This guide covers the module-first workflow for Apmatia.

Modules are the preferred way to package a feature when that feature can be isolated cleanly. Libraries still hold reusable implementation details, but modules are where new app-facing capabilities should usually start.

## Quick Start

If you just want the shortest path to a working module, do this:

1. Pick a slug and a human-friendly name.
2. Create the module scaffold.
3. Define the data models and repository layer.
4. Add a service layer for the actual logic.
5. Keep `actions.py`, `commands.py`, and `views.py` as thin descriptors.
6. Register the module and validate it.
7. Promote it when the draft is ready.

That is the whole game in one line:

`data model -> repository -> service -> descriptors -> registry -> interface`

If you want a narrative walkthrough of the IPE module we built during this task, see:

- [How We Made The IPE Module](./HOW_WE_MADE_IPE_MODULE.md)

If you want the module-to-Streamlit rendering story, including the schema-inference layer that now
drives list and create forms, see:

- [Streamlit Module Views](./STREAMLIT_MODULE_VIEWS.md)

The rest of this document is the deeper explanation and reference guide.

## Module Types

- Bundled modules live in `src/apmatia/modules/`
- Draft or agent-assisted modules live in `~/.apmatia/workspace/modules/`

Bundled modules are part of the application. Workspace modules are safe drafts that can be planned, scaffolded, inspected, edited, and validated before promotion.

The workspace root defaults to `~/.apmatia/workspace/modules/` and can be overridden with `APMATIA_WORKSPACE_ROOT`. If the environment variable is unavailable on the host, Apmatia also checks `~/.config/apmatia/config.json` for `workspace.root` before falling back to the home-directory default.

## What A Module Contains

A module packages a feature and registers it into the application registry.

Typical module pieces:

- module metadata
- actions
- tools
- commands
- views

## Metadata And Manifest Shape

Every module declares the same standardized metadata twice: declaratively in `manifest.toml`, so bootstrap can classify it before importing Python, and as `ModuleMetadata` in `module.py`, so the active registry has typed metadata. Keep the two declarations synchronized.

A new manifest should look like this:

```toml
[module]
module_id = "example"
name = "Example"
version = "0.1.0"
description = "A focused example module."
author = "Your Name"
status = "development"
category = "feature"
default_enabled = true
tags = ["example"]

[metadata]

[dependencies]
python = ">=3.10"
python_packages = []
system_packages = []
modules = []
tools = []
```

The matching runtime declaration is:

```python
from apmatia.core.registry import (
    ModuleCategory,
    ModuleMetadata,
    ModuleStatus,
)

EXAMPLE_MODULE = ModuleMetadata(
    module_id="example",
    name="Example",
    version="0.1.0",
    description="A focused example module.",
    author="Your Name",
    status=ModuleStatus.DEVELOPMENT,
    category=ModuleCategory.FEATURE,
    default_enabled=True,
    tags=("example",),
)
```

Use only `stable` and `development` for status. New modules default to development and should remain there while unfinished, experimental, incomplete, broken, or actively changing. Promote a module to stable only when it is suitable for ordinary users. Status is maturity, not runtime health: enabled, disabled, unavailable, dependency failure, and runtime error are separate concerns.

Use one of the declared singular categories: `core`, `infrastructure`, `feature`, `agent`, `tool`, `integration`, `interface`, `development`, or `other`.

Tags are stored as an immutable tuple at runtime. The `[metadata]` table remains available for arbitrary extension data, but never place `status`, `category`, `default_enabled`, or `tags` there in new repository-owned manifests. The loader can still consume legacy `[metadata].category` and `[metadata].tags` values, with first-class `[module]` values taking precedence.

## Stable-Only Activation

The application starts with `ui.show_development_modules = false`. Bootstrap reads manifests before importing module Python code for registration and activates only modules that are both stable and default-enabled. Inactive development modules do not register functionality, views, actions, commands, tools, providers, dedicated HTTP behavior, or background services.

The Module Manager view has an "Enable all modules" toggle for development work. Turning it on persists the setting and rebuilds the active registry. Turning it off restores the release-safe stable-only set. A module that starts background work must expose a `deactivate()` hook and stop that work when disabled.

For module views, prefer a small schema-first description over handwritten interface code. The
Streamlit adapter can infer list columns and basic create forms from module metadata when the view
describes its fields clearly enough.

That list is easy to say, but it is not always easy to understand. The short version is:

- `views` describe what the interface should show
- `actions` group related capabilities for a feature area
- `commands` are the concrete operations the interface can invoke
- `services` hold the actual business logic
- `tools` expose selected capabilities to agents

If you remember only one thing, remember this:

`views` and `commands` describe behavior, but `services` do the work.

Modules should not contain transport logic. They should define capabilities, not UI framework code or HTTP wiring.

## Actions, Commands, Services

These words are easy to mix up, so here is the practical distinction.

### Actions

An action is a named capability group.

Use an action when you want to say, “this module can do something in this area.”

In the IPE module, an action might represent:

- idea capture
- task management
- project management
- habit management
- calendar management

An action is not the thing that edits the database. It is optional organizational metadata for related views and tools; commands are registered directly under their module.

### Commands

A command is the concrete thing an interface or agent can invoke.

Commands do not belong to actions. Each command has a module-scoped identifier such as
`agents.list`. Modules with several independent resource families may add a meaningful command
namespace to avoid collisions, such as `ipe.idea.create`, without linking the command to an action.

The CLI is assembled from active command descriptors. `path` determines the nested shell command,
while `name`, `description`, and `metadata.input_fields` generate command help and typed flags.
Collection commands can omit `input_fields` when their matching view schema already describes the
create or edit fields. Commands without either schema remain executable through `--payload JSON`.

Use a command when you want to say, “run this specific operation.”

Examples:

- list all ideas
- create a new project
- edit an existing habit
- delete a calendar event

Commands should stay small and explicit. They should identify the operation, but they should not contain all the business rules themselves.

For the UI, commands should also carry enough metadata for the interface to decide how to render
the matching controls. When a command needs a form, prefer a field schema on the view metadata or
command metadata instead of writing a one-off Streamlit form.

### Services

A service is where the real logic belongs.

Use a service when you want to say, “given this request, what should actually happen?”

Services are the right place for:

- validation
- conversions
- cross-object workflows
- repository coordination
- ownership and permission checks
- business rules

For example, the IPE service layer should decide how to:

- convert a captured idea into a project
- convert a captured idea into a habit
- convert a captured idea into a calendar event
- preserve the source idea as provenance instead of deleting it
- update the right repository records in one unit of work

That means the flow should look like this:

`view -> command -> service -> repository`

The view describes the screen.
The command names the operation.
The service performs the work.
The repository stores the result.

## Recommended Workflow

1. Plan the module.
2. Create the scaffold.
3. Edit the workspace module files.
4. Validate the module.
5. Promote the module when it is ready.

For bundled modules, use the default module location. For draft work, use the workspace flag so the new module is created under `workspace/modules/<slug>/` or whichever path `APMATIA_WORKSPACE_ROOT` points to.

In practice, the planning step should answer four questions before you write code:

- what problem the module solves
- what the module name and slug should be
- which actions, tools, commands, and views belong in the module
- whether the work should stay in `workspace/modules/` or be promoted into `src/apmatia/modules/`

It is also worth answering one more question:

- where does the business logic live

For most real features, the answer should be a service layer inside a library, not the module descriptors themselves.

## A Simple Mental Model

If you are building a new feature and want to keep it easy, use this sequence:

1. Define the data model.
2. Define the repository layer.
3. Define the service layer.
4. Define module actions, commands, and views as thin descriptors.
5. Register the module into the application registry.
6. Let the interfaces render the views and call the commands through the API.

When a module exposes a collection view, the Streamlit adapter can now infer:

- table/list columns from view schema fields marked for list display
- create forms from view schema fields marked for create display
- empty state, title, and action buttons from the registry-backed view descriptor

The `ipe` module is the first bundled example that uses this path to ship real capture UI
without custom page code for the form itself.

That keeps the module easy to reason about and avoids stuffing business rules into the wrong file.

## CLI Commands

The module CLI is the easiest way to work with the module system from a shell:

```bash
apmatia module plan productivity
apmatia module create productivity --name "Productivity"
apmatia module validate productivity
apmatia module list
apmatia module show worksim
```

Workspace-aware examples:

```bash
apmatia module plan productivity --workspace --format json
apmatia module create productivity --workspace
apmatia module validate productivity --workspace --format json
apmatia module list --workspace
apmatia module show productivity --workspace
apmatia module files productivity --workspace
apmatia module read productivity actions.py --workspace
cat new_actions.py | apmatia module write productivity actions.py --workspace --stdin
```

If you are using tool calls instead of the CLI, the same workflow maps to these workspace tools:

- `plan_workspace_module`
- `create_workspace_module`
- `list_workspace_module_files`
- `read_workspace_module_file`
- `write_workspace_module_file`
- `validate_workspace_module`

Those tools all operate inside a draft module directory under `workspace/modules/<slug>/`.

## Scaffold Output

A module scaffold creates the expected starting files:

- `__init__.py`
- `manifest.toml`
- `module.py`
- `actions.py`
- `tools.py`
- `commands.py`
- `views.py`
- `README.md`
- `tests/`

The scaffold is intentionally small and boring. It gives you the standard module shape without inventing behavior.

## Validation

Validation checks that:

- the required files exist
- the manifest parses cleanly
- status and category values are supported
- first-class metadata has the correct types
- the Python files are syntactically valid
- `module.py` exposes `register(registry)`
- the module can register its metadata and descriptors into a fresh in-memory registry

Validation is read-only. It does not install, enable, or execute a module as part of application startup.

## Workspace Editing

Workspace module editing is restricted to files inside the matching workspace module directory.

Safety rules:

- no absolute paths
- no `..` traversal
- no writes outside `workspace/modules/<slug>/`
- UTF-8 text only for now

Use the workspace editor or the CLI wrappers to read, write, list, and delete draft files safely.

Typical draft module layout:

```text
workspace/modules/<slug>/
├── __init__.py
├── manifest.toml
├── module.py
├── actions.py
├── tools.py
├── commands.py
├── views.py
├── README.md
└── tests/
    └── test_<slug>_module.py
```

## Promotion Mindset

The long-term path is:

1. prototype in a workspace module
2. validate the module
3. inspect the generated descriptors
4. promote or copy the module into the bundled module set when it is ready
5. keep its status as `development` until it is suitable for ordinary users

The project should gradually move feature code into modules where it makes sense, while keeping shared implementation detail in libraries.

If you are running inside Docker, make sure the workspace volume is mounted and `APMATIA_WORKSPACE_ROOT` points at the mounted location. That keeps draft modules persistent and makes workspace tools fail fast when the mount is missing or unwritable.

When promoting a module, copy or move the finalized module from `workspace/modules/<slug>/` into `src/apmatia/modules/<slug>/` and re-run validation against the bundled location. Promotion into the bundled tree does not automatically make a module stable.

## Related Docs

- architecture: `docs/ARCHITECTURE.md`
- repository overview: `README.md`
