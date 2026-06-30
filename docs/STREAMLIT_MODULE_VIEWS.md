# Streamlit Module Views

The Streamlit interface renders module views through a small adapter layer in:

- `/home/nick/ServerData/repos/apmatia/src/interfaces/streamlit/module_views/`

The flow is:

1. A module registry view arrives as an opaque `ViewContribution`.
2. The adapter reads the registry metadata and resolves a Streamlit render model.
3. The adapter can infer list columns and create forms from a small schema embedded in the view metadata.
4. The page layer asks the API for the current items for that view.
5. The renderer draws the title, description, collection rows, empty state, action buttons, and any inferred create form.

Current support focuses on collection-style views with table-like row rendering and simple action buttons.
Unsupported render modes fail gracefully with a visible warning instead of crashing the page.

The minimal schema today is intentionally small:

- `fields`
- per-field flags for `list` and `create`
- field type hints such as `text`, `textarea`, `number`, `checkbox`, and `select`
- optional UI hints such as `label`, `placeholder`, `help_text`, `required`, and `default`
- optional create-form metadata such as title, description, submit label, and cancel label

This is enough for the first practical UI shape: idea capture in `apmatia_ipe`.

To render a view from the app, select a visible module from the left navigation and open one of its
views. The page layer now loads the items through the API and passes the resulting view descriptor to
the adapter automatically.
