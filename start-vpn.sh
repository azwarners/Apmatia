#!/bin/bash

# Start Apmatia for access through the host's trusted VPN.
# Usage: ./start-vpn.sh [core|streamlit|dev]
# Defaults to starting both services.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-dev}"

if [ "$#" -gt 1 ]; then
    echo "Usage: ./start-vpn.sh [core|streamlit|dev]"
    exit 1
fi

case "$MODE" in
    core|streamlit|dev)
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: ./start-vpn.sh [core|streamlit|dev]"
        exit 1
        ;;
esac

export APMATIA_DOCKER_BIND_HOST="0.0.0.0"
exec "$SCRIPT_DIR/start.sh" "$MODE"
