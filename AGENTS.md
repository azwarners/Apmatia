Apmatia is built around a collection of tiny, focused Python libraries. All business logic should live in libraries, while the application layer should stay thin and act only as orchestration and glue.

Feature work should generally move into modules when it fits the problem. Bundled modules live in `src/modules/`, and draft or agent-assisted work belongs in `workspace/modules/` until it is ready to be promoted.

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
