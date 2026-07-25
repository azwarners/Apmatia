Apmatia is built around tiny, focused Python modules. When a capability is being added or expanded, put the implementation in a bundled module under `src/apmatia/modules/` or a draft module under `workspace/modules/` instead of creating a top-level library package.

Module-specific helper code should live inside the module package itself. Foundational primitives that must be available before module bootstrap belong in `src/apmatia/core/`; they must not be modeled as activatable modules. The application layer should stay thin and act only as orchestration and glue.

User interfaces such as a CLI or web app must always use the API. Interfaces never call Apmatia core directly. Only the API gets to talk to the core. This is a strict boundary.

Tests are run with `./test.sh`.
The application is deployed with `./start.sh`.
After each code change task, run the full test suite and then redeploy the application.

For development iterations, deploy Apmatia to the LAN. Core deployments should bind to `0.0.0.0:8000`, and Streamlit deployments should bind to `0.0.0.0:8501`.
Always start the Streamlit interface as part of development work unless the user explicitly asks for core-only work. If a task changes code, verify the result by running the relevant tests and then redeploy both the core and Streamlit app locally before handing the work back.
When a change is clearly minor, low-risk, and directly supportive of the current work, make it proactively instead of stopping to ask for approval. If the change is larger, ambiguous, or has non-obvious consequences, pause and check first.

For the Streamlit app, do not rely on Streamlit's default multipage sidebar. The built-in page list (`app`, `landing`, `login`, `settings`) must stay hidden at all times, and only the custom sidebar navigation below the divider should be visible. Preserve both safeguards that enforce this: `.streamlit/config.toml` and the `--client.showSidebarNavigation false` flag in `scripts/entrypoint.sh`.

For browser clipboard actions in Streamlit, do not rely on iframe components or native `st.code` copy buttons. Use the reusable main-DOM helper in `src/interfaces/streamlit/components/clipboard_button.py` via `st.html(..., unsafe_allow_javascript=True)`, and hide the native Streamlit code-copy control when rendering custom message actions.

For the Streamlit app's custom upper-right menu, remember that Streamlit still renders a top header layer even when the toolbar is minimized. That invisible layer can cover or intercept custom controls placed at the top edge. Preserve the CSS safeguards in `src/interfaces/streamlit/app.py` that give `.apm-header-menu` a higher stacking order than `[data-testid="stHeader"]` and disable pointer events on the Streamlit header. When adding items to this menu, change only the menu contents unless the trigger/header stacking behavior is intentionally being revisited.

Module UI work should stay schema-first and adapter-driven. When adding or changing module views, update the registry-backed view metadata and the shared module-view adapter/schema layer rather than writing module-specific Streamlit screens. The `ipe` module is the reference example for schema-inferred list and create views.

Do not add new Streamlit pages under `src/apmatia/interfaces/streamlit/pages/` for module features. If a feature needs UI, expose it as a module view through the registry-backed module-view layer so the Streamlit shell stays replaceable.

When a module needs a guided setup action such as SSH key preparation, keep that action inside the module view form or view metadata instead of creating a new Streamlit page. Prefer a module command that the shared Streamlit module-view layer can invoke, and avoid burying first-run setup only in troubleshooting text.

## Module Metadata and Activation

Every bundled or workspace module must use the current first-class metadata contract in both `manifest.toml` and its runtime `ModuleMetadata`. The standardized fields are `author`, `status`, `category`, `default_enabled`, and `tags`; keep arbitrary extension data in `metadata`. Do not duplicate standardized fields inside the extension metadata dictionary or the manifest's `[metadata]` table.

Only these maturity values are supported:

- `stable`: suitable for ordinary use
- `development`: unfinished, experimental, incomplete, broken, or actively changing

New modules and manifests default to `development`. When classification is uncertain, use `development`. Do not invent alpha, beta, experimental, production, deprecated, or other status values. Runtime availability, enabled state, dependency failures, and errors are operational concerns and must not be added to `ModuleStatus`.

Only use categories declared by `ModuleCategory`: `core`, `infrastructure`, `feature`, `agent`, `tool`, `integration`, `interface`, `development`, or `other`. Use singular values.

The manifest is the bootstrap source of truth. Keep its standardized values synchronized with the runtime `ModuleMetadata` declared in `module.py`; tests enforce this parity. Existing legacy manifests may be read from `[metadata].category` and `[metadata].tags`, but all repository-owned manifests must use first-class values under `[module]`.

Apmatia starts in stable-only mode. Bootstrap must inspect manifests before importing module Python packages for registration, and development modules must not register actions, tools, commands, views, providers, dedicated routes, or background services while inactive. The persisted `ui.show_development_modules` setting and the Module Management "Enable all modules" toggle control this activation boundary. Filtering a navigation list is not sufficient. When adding a background service, provide a module deactivation hook that stops it when the application returns to stable-only mode.

When reporting changes back to the user, always include the full absolute path of at least one relevant file so it is obvious which repo instance and directory were touched. Prefer verbose path references when mentioning files in responses, especially after work that could otherwise be confused with a different checkout.

Do not use relative paths like `apmatia/...`, `./...`, or bare filenames when describing changed files to the user. Use absolute paths such as `/home/nick/ServerData/repos/apmatia/...` so there is no ambiguity about which checkout is being discussed.

Do not rely on UI hover labels, file cards, shortened link text, or repo-relative display names to establish the file path. When a file is mentioned in a response, the absolute path must be written explicitly in the message body itself.

## Destructive Changes

Do not delete, rename, or remove any existing module, package, directory, or substantial block of code unless the user explicitly names the exact target and clearly asks for that deletion.
If a request is ambiguous, incomplete, or could be interpreted as changing a different module, ask for clarification before making any destructive change.
Never infer that an existing module should be removed just because a new module is being added or a refactor is in progress.
When asked to restore or revert work, only restore the files or paths actually changed in the current task unless the user explicitly requests a broader rollback.
Before deleting any directory that contains code, summarize exactly what will be removed. A user request that explicitly names the target and asks for its deletion is sufficient confirmation; do not ask again.
