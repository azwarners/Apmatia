# How We Made The Apmatia IPE Module

This document records the path we took to build the `apmatia_ipe` module.

The point is not just to preserve history. It is to show how to think about a new module in Apmatia without getting lost in the architecture.

## 1. Start With The Module Skeleton

We began by creating a bundled module under:

- `/home/nick/ServerData/repos/apmatia/src/modules/apmatia_ipe/`

At that stage the module only needed the standard scaffold files:

- `__init__.py`
- `manifest.toml`
- `module.py`
- `actions.py`
- `tools.py`
- `commands.py`
- `views.py`
- `README.md`
- `tests/`

The first goal was not to solve the product problem. It was to prove that the architecture could hold a real feature package.

## 2. Define The Core Data Types

We then created the IPE data classes.

The original idea was a simple productivity environment with:

- idea capture
- task tracking
- project tracking
- habit tracking
- calendar events

We also aligned the objects with the shared Apmatia ownership model by inheriting from `ApmatiaObject`.

That gave each object:

- `id`
- `owner_user_id`
- `owner_group_id`
- `mode`
- timestamps

The important design choice was to make the records shareable across Apmatia instead of inventing a separate ownership system for IPE.

## 3. Add Conversion Behavior To Ideas

We realized that captured ideas should not just be edited in place.

Instead, an idea should be able to create a new object of another type, while keeping the original idea as provenance.

So we added conversion helpers on `CapturedIdea`:

- `convert_to_project(...)`
- `convert_to_habit(...)`
- `convert_to_calendar_event(...)`

Those methods do three things:

1. create the new target object
2. link the new object back to the source idea
3. mark the original idea as converted instead of deleting it

That keeps the capture history intact and makes the workflow safer.

## 4. Add Persistence

Next we introduced storage.

The IPE module needed actual repositories, not just in-memory objects, so we built SQLite-backed repositories for:

- ideas
- tasks
- projects
- habits
- calendar events

Each repository follows the same pattern:

- `create`
- `get`
- `list_all`
- `update`
- `delete`

This was the point where the module stopped being just a sketch and became a real data layer.

## 5. Define Views As Pure Descriptors

We wanted the module to stay independent of Streamlit.

So the views were defined as data, not UI code.

Each object type got a collection view descriptor that says:

- what object type it represents
- what commands exist for it
- what labels to use
- what empty-state message to show

For the first production-capable UI path, we added a minimal schema layer to the view metadata.
That schema is intentionally small but extensible:

- fields can be marked for list display
- fields can be marked for create display
- field type hints can steer the Streamlit widget choice
- labels, placeholders, and visibility can be overridden locally when the inferred default is not enough

That let the Streamlit adapter infer the Ideas capture form from the module model instead of
handwriting a one-off page.

That means Streamlit, CLI, or any future interface can render the collection however it wants without the module importing the UI framework directly.

## 6. Separate Actions And Commands

Once the views existed, we made the command structure more explicit.

The module now describes:

- actions for each object collection
- commands for list/create/edit/delete
- views for each collection screen

That separation keeps the module easier to understand:

- actions group the area
- commands perform the operation
- views describe the presentation

## 7. Validate The Module In Tests

We added tests for:

- module registration
- conversion behavior
- repository round-trips
- registry visibility
- CLI snapshots

The tests were useful for catching the architectural mismatch between what we intended and what the registry actually exposed.

## 8. Keep The Boundaries Clean

The biggest lesson from the module build was this:

The module should describe the feature, but the service layer should implement the feature.

That means:

- `views.py` should not know about Streamlit
- `actions.py` should not contain business logic
- `commands.py` should not become a dumping ground for workflows
- repositories should not decide product behavior
- services should own the actual use cases

For IPE, the next step is a service layer that orchestrates repository calls for workflows like:

- convert idea to project
- convert idea to habit
- convert idea to calendar event
- create next actions from existing work
- compute what the user should work on now

## 9. Current State

At the end of this phase, the module has:

- a module scaffold
- shared Apmatia ownership
- mutable productivity objects
- idea conversion helpers
- SQLite persistence
- pure view descriptors
- registered actions and commands
- tests proving the behavior
- a schema-driven Streamlit adapter path for list views and idea capture

The IPE module also serves as the first bundled example showing how new functionality can be added
through modules without editing a bespoke page for every screen.

That is enough to keep building the productivity assistant in a clean way.

## 10. What Comes Next

The next natural step is a service layer for IPE.

That service layer should sit above the repositories and below the API, and it should handle:

- CRUD orchestration
- conversion workflows
- triage logic
- recommendation logic for “what should I work on now?”
- agent-facing tool behavior

Future UI work should continue to extend the schema rather than introducing module-specific Streamlit
code. The goal is that module authors define behavior and metadata once, and the interface layer
renders the right controls automatically.

If we keep that separation disciplined, the module stays easy to extend without turning into a monolith.
