#!/bin/bash
set -euo pipefail

docker compose down --remove-orphans
docker rm -f apmatia-app >/dev/null 2>&1 || true
