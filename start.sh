#!/bin/bash
set -euo pipefail

APP_VERSION="$(cat VERSION 2>/dev/null || echo 'unknown')"
echo "Starting Apmatia version: ${APP_VERSION}"

# Ensure app restarts with a fresh container and rebuilt image so UI/code edits are always picked up.
docker compose down --remove-orphans

# If an older deploy directory started Apmatia as a different compose project,
# remove that container too so port 8000 always points at this working tree.
if docker ps -a --format '{{.Names}}' | grep -qx 'apmatia-app'; then
  docker rm -f apmatia-app >/dev/null 2>&1 || true
fi

docker compose up --build --force-recreate
