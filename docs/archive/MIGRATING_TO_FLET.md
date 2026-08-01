# Migrating Apmatia to Flet

## Overview

This guide documents the architectural boundary between Apmatia's portable view contract and the Flet GUI adapter. The goal is to replace Streamlit with Flet while preserving all user-visible behavior.

## Current State

### What Already Works

1. **Portable View Contract**: The `core/view_contract/` package defines version 1 models for:
   - Component trees (page, stack, columns, tabs, panel, card, collection, table, form, field, text, markdown, status, notice, actions, navigation, detail, timeline, message, composer, terminal, progress, checklist, tree, expander)
   - Data sources (singleton, collection, stream, tree)
   - State definitions (event, view, session, server scopes)
   - Actions and intents
   - Effects (refresh_source, refresh_view, set_state, clear_state, select_item, navigate, open_panel, close_panel, show_notification, start_polling, stop_polling, download)
   - Refresh policies (manual, on_intent, poll, stream modes)

2. **Module View Specifications**: All production modules declare view contributions in `views.py` files. Some already use the portable `ViewComponent` tree (discuss, agent_loops), while others still use the legacy `metadata.ui.render_mode` shorthand (agents, users, agent_tools, memory_manager).

3. **API Boundary**: The internal API exposes normalized view documents and view models through HTTP. A second adapter (text_adapter) proves the boundary is framework-neutral.

4. **Shell Independence**: The Streamlit shell no longer contains module-specific branches. Navigation flows through generic module catalog and route state.

## What You Need to Build

### 1. Flet Adapter Structure

```
interfaces/flet/
├── __init__.py
├── flet_renderer.py      # Maps ViewComponent to Flet widgets
├── components/
│   ├── __init__.py
│   ├── page.py           # flet.Container with vertical layout
│   ├── stack.py          # flet.Stack
│   ├── columns.py        # flet.Row with expand=True
│   ├── tabs.py           # flet.Tabs
│   ├── panel.py          # flet.Container with border/title
│   ├── card.py           # flet.Card
│   ├── collection.py     # flet.DataTable or ListView
│   ├── table.py          # flet.DataTable
│   ├── form.py           # flet.Form or Container with controls
│   ├── field.py          # flet.TextField, Dropdown, Checkbox, etc.
│   ├── text.py           # flet.Text
│   ├── markdown.py       # flet.Markdown
│   ├── status.py         # flet.Chip or Text with color
│   ├── notice.py         # flet.Alert or Banner
│   ├── actions.py        # flet.ElevatedButton, IconButton
│   ├── navigation.py     # flet.ListTile in ListView
│   ├── detail.py         # flet.Container with key-value pairs
│   ├── timeline.py       # flet.ListView with message cards
│   ├── message.py        # flet.Card with speaker/text/timestamp
│   ├── composer.py       # flet.TextField + send button
│   ├── terminal.py       # flet.ListView with monospace text
│   ├── progress.py       # flet.CircularProgressIndicator
│   ├── checklist.py      # flet.ListTile with Checkbox
│   ├── tree.py           # flet.TreeView
│   └── expander.py       # flet.Expander
├── state.py              # Flet session-state adapter
├── effects.py            # Flet effect executor
├── shell.py              # Flet navigation, auth shell
└── api_client.py         # Flet-specific HTTP client (optional)
```

### 2. Component Mapping Reference

| View Contract Component | Flet Widget | Notes |
|------------------------|-------------|-------|
| page | flet.Container (vertical, expand=True) | Root container |
| stack | flet.Stack | Overlapping children |
| columns | flet.Row (spacing, expand) | Respect column ratios |
| tabs | flet.Tabs | TabIndex for selection |
| panel | flet.Container (border, padding) | Title in header |
| card | flet.Card (elevation) | Optional shadow |
| collection | flet.DataTable or ListView | Use DataTable for tabular |
| table | flet.DataTable | Column headers |
| form | flet.Container (vertical) | Wrap in flet.Form if needed |
| field (text) | flet.TextField | Single-line |
| field (textarea) | flet.TextField (multiline=True) | |
| field (number) | flet.TextField (keyboard_type=number) | Validate range |
| field (checkbox) | flet.Checkbox | |
| field (select) | flet.Dropdown | Options from data source |
| field (multiselect) | flet.Dropdown (multi_select=True) | |
| field (date) | flet.DateField or DatePicker | |
| field (password) | flet.TextField (obscure=True) | |
| text | flet.Text | |
| markdown | flet.Markdown | |
| status | flet.Chip or Text (color) | Use color for state |
| notice | flet.Alert or Banner | Warning/error/success |
| actions | flet.ElevatedButton or IconButton | Style maps to variant |
| navigation | flet.ListTile (selected) | Click emits intent |
| detail | flet.Container (row of key-value) | |
| timeline | flet.ListView (vertical) | Message cards |
| message | flet.Card (speaker + text) | Timestamp if available |
| composer | flet.TextField + IconButton | Send button triggers intent |
| terminal | flet.ListView (monospace) | Append-only for streaming |
| progress | flet.CircularProgressIndicator | Spinning or value |
| checklist | flet.ListTile + Checkbox | Toggle emits intent |
| tree | flet.TreeView | Expand/collapse |
| expander | flet.Expander | Collapsible section |

### 3. State Management

Flet uses `page.session_state` instead of Streamlit's `st.session_state`. The adapter must:

1. Map declared view state keys to `page.session_state`
2. Handle the four scopes:
   - `event`: Transient, cleared after intent
   - `view`: Persists while view is active
   - `session`: Persists across navigation
   - `server`: Persists through API calls
3. Implement `set_state`, `clear_state`, `select_item` effects
4. Handle `st.rerun()` equivalent via `page.update()`

### 4. Effects and Navigation

Flet doesn't have `st.rerun()`. Instead:

1. Use `page.update()` to refresh the view
2. Implement `navigate` effect by changing `page.route`
3. Use `page.snack_bar` for `show_notification`
4. Handle `refresh_source` by re-fetching data source
5. Implement `start_polling` with `page.add_timer()` or async loop
6. Implement `stop_polling` by cancelling timer

### 5. Rich Interaction Patterns

#### Discussion Timeline
- Use `flet.ListView` with `expand=True`
- Each message is a `flet.Card` with `flet.Text` for speaker and content
- Composer is `flet.TextField` + `IconButton` (send)
- Polling: Use `page.add_timer(interval, callback)` to refresh

#### Agent Loops Terminal
- Use `flet.ListView` with `flet.Text` (monospace)
- Append-only: Use `list_view.add()` and `page.update()`
- Progress indicator: `flet.CircularProgressIndicator`
- Checklist: `flet.ListTile` with `Checkbox`

#### Master/Detail Navigation
- Use `flet.Row` with `navigation` panel (left) and `detail` panel (right)
- Navigation panel: `flet.ListView` of `flet.ListTile`
- Selection: Set `selected=True` on active item
- Intent: Emit `select_item` effect on click

### 6. Authentication Shell

The Flet shell should:

1. Check `page.session_state["authenticated_user"]` on route change
2. Redirect to `login` view if not authenticated
3. Use the auth module's portable login/register documents
4. Implement logout as `set_state` + `navigate` effect

### 7. Theming

Flet supports `theme` property on `app`:

1. Map `ui_theme_preference` to Flet theme (light/dark)
2. Use `flet.Theme` for custom colors
3. Respect `system` mode by detecting `theme_mode`

## What Needs Research

### 1. Flet Component Equivalents

The following contract components need Flet-specific research:

- **timeline**: Best Flet pattern for chat-like scrolling?
- **composer**: How to handle attachments in Flet?
- **checklist**: How to sync checkbox state with intent?
- **terminal**: Does Flet support append-only streaming efficiently?
- **tree**: How to handle nested expand/collapse with intents?

### 2. Flet-Specific Patterns

- How to handle `flet.Fab` (floating action button) for primary actions?
- How to implement modal dialogs for confirmations?
- How to handle file uploads in Flet forms?
- How to handle image previews in Flet composer?
- How to implement split-pane layouts (master/detail)?

### 3. Flet State Management

- Does Flet have a concept of `view` vs `session` scope?
- How to handle `event`-scoped state (transient)?
- How to implement `select_item` effect (highlight selection)?

### 4. Flet Navigation

- How to implement `navigate` effect (change route)?
- How to handle back/forward navigation?
- How to preserve state across navigation?

### 5. Flet Polling

- How to implement `start_polling` with proper cleanup?
- How to handle `stop_when` conditions?
- How to implement `reject_stale` for streaming?

### 6. Flet Styling

- How to map `style` (primary/secondary/danger) to Flet button variants?
- How to implement `visible_when` conditions (show/hide)?
- How to handle `enabled_when` conditions (disable button)?

## Migration Sequence

### Phase 1: Port Component Mappings

1. Create `interfaces/flet/components/` directory
2. Implement 20+ component renderers
3. Validate each component against the contract
4. Write unit tests for each component

### Phase 2: Port Shell and Navigation

1. Create `interfaces/flet/shell.py`
2. Implement authentication gating
3. Implement generic navigation catalog
4. Implement route state adapter

### Phase 3: Port Effects and State

1. Create `interfaces/flet/state.py`
2. Implement `set_state`, `clear_state`, `select_item`
3. Create `interfaces/flet/effects.py`
4. Implement `navigate`, `refresh_source`, `show_notification`
5. Implement `start_polling`, `stop_polling`

### Phase 4: Port Rich Views

1. Implement Discussion timeline/composer
2. Implement Agent Loops terminal/checklist
3. Test live update patterns

### Phase 5: Full Integration

1. Replace Streamlit with Flet in `main.py`
2. Run behavioral parity tests
3. Remove Streamlit dependencies

## Testing Strategy

### Component Tests

- Each component renderer should have unit tests
- Test with valid and invalid contract documents
- Verify intent emission for interactive components

### Integration Tests

- Test full view documents through the Flet adapter
- Verify effect execution
- Test navigation flows

### Parity Tests

- Compare Flet behavior with Streamlit behavior
- Test representative journeys (login, create agent, send message, start task)

## Known Gaps

1. **Streamlit-specific features**: CSS workarounds, clipboard integration, DOM selectors - these need Flet equivalents
2. **Browser-specific behavior**: Streamlit has browser integration (cookies, local storage) - Flet needs equivalent
3. **Performance**: Flet's ListView may have different performance characteristics for large collections
4. **Mobile considerations**: Android client may need touch-specific adjustments

## Assumptions

1. Flet has widget equivalents for all 20+ contract components
2. Flet's `page.session_state` is sufficient for view/session scope state
3. Flet's event system can emit intents equivalent to Streamlit's
4. Flet's theming system supports light/dark/system modes
5. Flet's polling/timer mechanism supports the `poll` refresh mode

## Next Steps

1. Read Flet documentation for component equivalents
2. Build a minimal Flet hello-world that renders a contract document
3. Implement the 20+ component renderers
4. Build the shell and navigation
5. Test with existing view documents
6. Iterate based on gaps discovered


Google's recommendation for a Flet agent loop output shell:

```
import flet as ft

def main(page: ft.Page):
    page.title = "Flet Shell"
    
    output_list = ft.ListView(expand=True, auto_scroll=True)
    input_field = ft.TextField(hint_text="Enter command...", border="none")

    def run_command(e):
        cmd = input_field.value
        output_list.controls.append(ft.Text(f"$ {cmd}"))
        # Process command logic here
        output_list.controls.append(ft.Text(f"Output for: {cmd}"))
        input_field.value = ""
        page.update()

    input_field.on_submit = run_command

    # Stack layout for layering terminal elements
    shell_stack = ft.Stack(
        [
            ft.Container(content=output_list, padding=10),
            ft.Positioned(
                bottom=0, left=0, right=0,
                child=ft.Container(content=input_field, bgcolor=ft.colors.BLACK12)
            ),
        ],
        expand=True,
    )

    page.add(shell_stack)

ft.app(target=main)
```