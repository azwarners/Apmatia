# Creating Modules

This guide covers the module-first workflow for Apmatia.

Modules are the preferred way to package a feature when that feature can be isolated cleanly. Libraries still hold reusable implementation details, but modules are where new app-facing capabilities should usually start.

## Module Types

- Bundled modules live in `src/modules/`
- Draft or agent-assisted modules live in `workspace/modules/`

Bundled modules are part of the application. Workspace modules are safe drafts that can be planned, scaffolded, inspected, edited, and validated before promotion.

## What A Module Contains

A module packages a feature and registers it into the application registry.

Typical module pieces:

- module metadata
- actions
- tools
- commands
- views

Modules should not contain transport logic. They should define capabilities, not UI framework code or HTTP wiring.

## Recommended Workflow

1. Plan the module.
2. Create the scaffold.
3. Edit the workspace module files.
4. Validate the module.
5. Promote the module when it is ready.

For bundled modules, use the default module location. For draft work, use the workspace flag so the new module is created under `workspace/modules/<slug>/`.

## CLI Commands

The module CLI is the easiest way to work with the module system from a shell:

```bash
apmatia module plan productivity
apmatia module create productivity --name "Productivity"
apmatia module validate productivity
apmatia module list
apmatia module show example
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

## Promotion Mindset

The long-term path is:

1. prototype in a workspace module
2. validate the module
3. inspect the generated descriptors
4. promote or copy the module into the bundled module set when it is ready

The project should gradually move feature code into modules where it makes sense, while keeping shared implementation detail in libraries.

## Related Docs

- architecture: `docs/ARCHITECTURE.md`
- repository overview: `README.md`
