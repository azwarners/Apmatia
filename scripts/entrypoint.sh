#!/bin/bash

# Entrypoint script that respects the MODE build argument
# Usage: Called automatically by container, or manually with MODE env var

MODE="${MODE:-core}"

# If a command is passed (like 'pytest'), run it instead
if [ -n "$*" ]; then
    exec "$@"
elif [ "$MODE" = "streamlit" ]; then
    exec python -m streamlit run src/interfaces/streamlit/app.py --server.port 8501 --server.address "0.0.0.0" --client.showSidebarNavigation false
else
    exec python scripts/run.py
fi
