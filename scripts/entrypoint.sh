#!/bin/bash

# Entrypoint script that respects the MODE build argument
# Usage: Called automatically by container, or manually with MODE env var

MODE="${MODE:-core}"

# If a command is passed (like 'pytest'), run it instead
if [ -n "$*" ]; then
    exec "$@"
elif [ "$MODE" = "streamlit" ]; then
    exec python3 scripts/run_streamlit.py --client.showSidebarNavigation false
else
    exec python3 scripts/run.py
fi
