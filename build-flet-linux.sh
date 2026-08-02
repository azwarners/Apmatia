#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLET_BIN="${FLET_BIN:-$SCRIPT_DIR/.venv/bin/flet}"
OUTPUT_DIR="${FLET_OUTPUT_DIR:-$SCRIPT_DIR/build/flet-linux}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    sed -n '1,120p' "$SCRIPT_DIR/build-flet-linux.sh"
    exit 0
fi

if [[ ! -x "$FLET_BIN" ]]; then
    echo "Flet CLI was not found at $FLET_BIN." >&2
    echo "Install the matching Flet CLI first: uv pip install flet-cli==0.86.4" >&2
    exit 1
fi

if ! "$SCRIPT_DIR/.venv/bin/python" -c 'from importlib.metadata import version; version("flet-cli")' >/dev/null 2>&1; then
    echo "The matching Flet CLI is not installed in $SCRIPT_DIR/.venv." >&2
    echo "Install it first: uv pip install flet-cli==0.86.4" >&2
    exit 1
fi

echo "Building the Apmatia Linux Client into $OUTPUT_DIR"
exec "$FLET_BIN" build linux "$SCRIPT_DIR/src/apmatia/interfaces/flet/linux" \
    --yes \
    --output "$OUTPUT_DIR" \
    --project apmatia \
    --artifact apmatia-linux \
    --product Apmatia \
    --org com.apmatia \
    --bundle-id com.apmatia.linux
