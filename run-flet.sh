#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'USAGE'
Usage: ./run-flet.sh

Launches the native Apmatia Linux Client using the project-local Python environment.
Start Apmatia Core separately with ./start.sh core before launching the client.
USAGE
    exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Apmatia's project environment was not found at $SCRIPT_DIR/.venv." >&2
    echo "Create the project environment and install dependencies before launching Flet." >&2
    exit 1
fi

# Flet installs a small desktop runtime on first launch. Copying its cached
# wheels is reliable across the repository and user-cache filesystems and
# avoids a noisy hardlink fallback warning.
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

echo "Launching the Apmatia Linux Client. Ensure Apmatia Core is running on /api first."
exec "$PYTHON_BIN" -m apmatia.interfaces.flet.linux.app "$@"
