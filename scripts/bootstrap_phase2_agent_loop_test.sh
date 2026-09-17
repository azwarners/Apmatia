#!/usr/bin/env bash

set -euo pipefail

# Provision durable resources used by the authenticated Phase 2 API tests.
# The deterministic model/tool implementations remain pytest-owned because
# providers are registered in the running Python process.

phase2_root="${PHASE2_TEST_ROOT:-${TMPDIR:-/tmp}/apmatia-phase2-test}"
api_url="${APMATIA_API_URL:-http://127.0.0.1:8000/api}"
username="${PHASE2_TEST_USERNAME:-phase2-test}"
password="${PHASE2_TEST_PASSWORD:-phase2-test-password}"
agent_name="${PHASE2_TEST_AGENT_NAME:-Phase 2 Test Assistant}"
config_dir="$phase2_root/config"
session_file="$config_dir/cli-session.json"
resource_file="$phase2_root/resources.env"

mkdir -p "$config_dir"

export APMATIA_API_URL="$api_url"
export APMATIA_CONFIG_DIR="$config_dir"
export APMATIA_CLI_SESSION_FILE="$session_file"

if ! apmatia register "$username" --password "$password" >/dev/null 2>&1; then
    apmatia login "$username" --password "$password" >/dev/null
fi

agent_json="$(apmatia agents create --name "$agent_name" --format json)"
agent_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["item"]["id"])' <<<"$agent_json")"

mkdir -p "$phase2_root"
{
    printf 'PHASE2_TEST_ROOT=%q\n' "$phase2_root"
    printf 'PHASE2_TEST_USERNAME=%q\n' "$username"
    printf 'PHASE2_TEST_PASSWORD=%q\n' "$password"
    printf 'PHASE2_TEST_AGENT_ID=%q\n' "$agent_id"
    printf 'APMATIA_API_URL=%q\n' "$api_url"
    printf 'APMATIA_CONFIG_DIR=%q\n' "$config_dir"
    printf 'APMATIA_CLI_SESSION_FILE=%q\n' "$session_file"
} > "$resource_file"
chmod 600 "$resource_file"

printf 'Provisioned Phase 2 resources.\n'
printf 'Resource environment: %s\n' "$resource_file"
printf 'Agent ID: %s\n' "$agent_id"
