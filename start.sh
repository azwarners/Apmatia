#!/bin/bash

# Apmatia Docker startup script
# Usage: ./start.sh [core|streamlit]
#   core     - Start the Apmatia core container on localhost:8000 (default)
#   streamlit - Start the Streamlit interface container

set -e

MODE="core"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

for arg in "$@"; do
    case "$arg" in
        core|streamlit)
            MODE="$arg"
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./start.sh [core|streamlit]"
            exit 1
            ;;
    esac
done

BUILD_ARGS=(--build-arg MODE="$MODE")

if [ "$MODE" = "core" ]; then
    IMAGE_NAME="apmatia"
    CONTAINER_NAME="apmatia"
    echo "Building Apmatia core container..."
    docker build -t "$IMAGE_NAME" "${BUILD_ARGS[@]}" .
elif [ "$MODE" = "streamlit" ]; then
    IMAGE_NAME="apmatia-streamlit"
    CONTAINER_NAME="apmatia-streamlit"
    echo "Building Apmatia Streamlit interface container..."
    docker build -t "$IMAGE_NAME" "${BUILD_ARGS[@]}" .
else
    echo "Unknown mode: $MODE"
    echo "Usage: ./start.sh [core|streamlit]"
    exit 1
fi

APMATIA_HOME_HOST="${APMATIA_HOME:-$HOME/.apmatia}"
APMATIA_DATA_DIR_HOST="${APMATIA_DATA_DIR:-$HOME/.local/share/apmatia}"
APMATIA_CONFIG_DIR_HOST="${APMATIA_CONFIG_DIR:-$HOME/.config/apmatia}"
APMATIA_WORKSPACE_DIR_HOST="${APMATIA_WORKSPACE_DIR:-$HOME/.apmatia/workspace}"
APMATIA_WORKSPACE_ROOT_HOST="$APMATIA_WORKSPACE_DIR_HOST/modules"
APMATIA_GGUF_DIRECTORY_HOST="${APMATIA_GGUF_DIRECTORY:-}"
APMATIA_GGUF_DIRECTORIES_HOST="${APMATIA_GGUF_DIRECTORIES:-}"
APMATIA_LLAMA_SERVER_LOG_DIR_HOST="${APMATIA_LLAMA_SERVER_LOG_DIR:-${LLAMA_LOG_DIR:-}}"
APMATIA_CONTAINER_HOME="/home/apmatia"
APMATIA_CONTAINER_HOME_DIR="$APMATIA_CONTAINER_HOME/.apmatia"
APMATIA_CONTAINER_DATA_DIR="$APMATIA_CONTAINER_HOME/.local/share/apmatia"
APMATIA_CONTAINER_CONFIG_DIR="$APMATIA_CONTAINER_HOME/.config/apmatia"
APMATIA_CONTAINER_WORKSPACE_DIR="$APMATIA_CONTAINER_HOME_DIR/workspace"

repair_host_permissions() {
    local host_dir="$1"
    local container_dir="$2"
    local host_uid
    local host_gid

    host_uid="$(id -u)"
    host_gid="$(id -g)"

    echo "Repairing permissions for $host_dir..."
    docker run --rm \
        -v "$host_dir":"$container_dir" \
        --entrypoint /bin/bash \
        "$IMAGE_NAME" \
        -lc "mkdir -p '$container_dir' && chown -R ${host_uid}:${host_gid} '$container_dir'"
}

ensure_host_permissions() {
    local host_dir="$1"
    local container_dir="$2"

    mkdir -p "$host_dir" 2>/dev/null || true
    if [ ! -d "$host_dir" ] || [ ! -w "$host_dir" ]; then
        repair_host_permissions "$host_dir" "$container_dir"
    fi
    mkdir -p "$host_dir"
}

if [ -z "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST" ] && [ -f "$APMATIA_CONFIG_DIR_HOST/config.json" ]; then
    APMATIA_LLAMA_SERVER_LOG_DIR_HOST="$(python3 -c 'import json, sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

value = ""
if isinstance(data, dict):
    llama_server = data.get("llama_server")
    if isinstance(llama_server, dict):
        value = llama_server.get("log_dir") or ""

print(str(value).strip())' "$APMATIA_CONFIG_DIR_HOST/config.json")"
fi

if [ -z "$APMATIA_GGUF_DIRECTORIES_HOST" ] && [ -f "$APMATIA_CONFIG_DIR_HOST/config.json" ]; then
    APMATIA_GGUF_DIRECTORIES_HOST="$(python3 -c 'import json, sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

values = []
if isinstance(data, dict):
    ai_model_manager = data.get("ai_model_manager")
    if isinstance(ai_model_manager, dict):
        raw_values = ai_model_manager.get("gguf_directories") or []
        if isinstance(raw_values, list):
            values = [str(item).strip() for item in raw_values if str(item).strip()]
        if not values:
            value = ai_model_manager.get("gguf_directory") or ""
            if value:
                values = [str(value).strip()]

print("\n".join(values))' "$APMATIA_CONFIG_DIR_HOST/config.json")"
fi

if [ -z "$APMATIA_GGUF_DIRECTORIES_HOST" ] && [ -n "$APMATIA_GGUF_DIRECTORY_HOST" ]; then
    APMATIA_GGUF_DIRECTORIES_HOST="$APMATIA_GGUF_DIRECTORY_HOST"
fi

if [ -n "$APMATIA_GGUF_DIRECTORIES_HOST" ]; then
    APMATIA_GGUF_DIRECTORIES_HOST="$(printf '%s' "$APMATIA_GGUF_DIRECTORIES_HOST" | tr ':' '\n')"
fi

ensure_host_permissions "$APMATIA_HOME_HOST" "$APMATIA_HOME_HOST"
ensure_host_permissions "$APMATIA_DATA_DIR_HOST" "$APMATIA_DATA_DIR_HOST"
ensure_host_permissions "$APMATIA_CONFIG_DIR_HOST" "$APMATIA_CONFIG_DIR_HOST"
mkdir -p "$APMATIA_WORKSPACE_ROOT_HOST"
if [ -n "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST" ]; then
    mkdir -p "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
fi

# Stop and remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
fi

# Run the container
echo "Starting $CONTAINER_NAME..."
if [ "$MODE" = "streamlit" ]; then
    LOG_DIR_ARGS=()
    if [ -n "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST" ]; then
        LOG_DIR_ARGS+=(
            -v "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST":"$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
            -e APMATIA_LLAMA_SERVER_LOG_DIR="$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
        )
    fi
    GGUF_DIR_ARGS=()
    if [ -n "$APMATIA_GGUF_DIRECTORIES_HOST" ]; then
        GGUF_DIRECTORY_ENV=""
        GGUF_DIRECTORY_FIRST=""
        while IFS= read -r gguf_directory_host; do
            if [ -z "$gguf_directory_host" ] || [ ! -d "$gguf_directory_host" ]; then
                continue
            fi
            GGUF_DIR_ARGS+=(
                -v "$gguf_directory_host":"$gguf_directory_host"
            )
            if [ -z "$GGUF_DIRECTORY_FIRST" ]; then
                GGUF_DIRECTORY_FIRST="$gguf_directory_host"
            fi
            if [ -z "$GGUF_DIRECTORY_ENV" ]; then
                GGUF_DIRECTORY_ENV="$gguf_directory_host"
            else
                GGUF_DIRECTORY_ENV="$GGUF_DIRECTORY_ENV:$gguf_directory_host"
            fi
        done <<EOF
$APMATIA_GGUF_DIRECTORIES_HOST
EOF
        if [ -n "$GGUF_DIRECTORY_ENV" ]; then
            GGUF_DIR_ARGS+=(
                -e APMATIA_GGUF_DIRECTORY="$GGUF_DIRECTORY_FIRST"
                -e APMATIA_GGUF_DIRECTORIES="$GGUF_DIRECTORY_ENV"
            )
        fi
    fi
    docker run \
        --name "$CONTAINER_NAME" \
        -p 0.0.0.0:8501:8501 \
        -v "$REPO_ROOT":/app \
        -v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR" \
        -v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR" \
        -v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR" \
        -v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR" \
        -e HOME="$APMATIA_CONTAINER_HOME" \
        -e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR" \
        -e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR" \
        -e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules" \
        --user "$(id -u):$(id -g)" \
        "${LOG_DIR_ARGS[@]}" \
        "${GGUF_DIR_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$IMAGE_NAME" /app/scripts/entrypoint.sh
else
    LOG_DIR_ARGS=()
    if [ -n "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST" ]; then
        LOG_DIR_ARGS+=(
            -v "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST":"$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
            -e APMATIA_LLAMA_SERVER_LOG_DIR="$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
        )
    fi
    GGUF_DIR_ARGS=()
    if [ -n "$APMATIA_GGUF_DIRECTORIES_HOST" ]; then
        GGUF_DIRECTORY_ENV=""
        GGUF_DIRECTORY_FIRST=""
        while IFS= read -r gguf_directory_host; do
            if [ -z "$gguf_directory_host" ] || [ ! -d "$gguf_directory_host" ]; then
                continue
            fi
            GGUF_DIR_ARGS+=(
                -v "$gguf_directory_host":"$gguf_directory_host"
            )
            if [ -z "$GGUF_DIRECTORY_FIRST" ]; then
                GGUF_DIRECTORY_FIRST="$gguf_directory_host"
            fi
            if [ -z "$GGUF_DIRECTORY_ENV" ]; then
                GGUF_DIRECTORY_ENV="$gguf_directory_host"
            else
                GGUF_DIRECTORY_ENV="$GGUF_DIRECTORY_ENV:$gguf_directory_host"
            fi
        done <<EOF
$APMATIA_GGUF_DIRECTORIES_HOST
EOF
        if [ -n "$GGUF_DIRECTORY_ENV" ]; then
            GGUF_DIR_ARGS+=(
                -e APMATIA_GGUF_DIRECTORY="$GGUF_DIRECTORY_FIRST"
                -e APMATIA_GGUF_DIRECTORIES="$GGUF_DIRECTORY_ENV"
            )
        fi
    fi
    docker run \
        --name "$CONTAINER_NAME" \
        -p 0.0.0.0:8000:8000 \
        -v "$REPO_ROOT":/app \
        -v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR" \
        -v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR" \
        -v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR" \
        -v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR" \
        -e HOME="$APMATIA_CONTAINER_HOME" \
        -e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR" \
        -e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR" \
        -e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules" \
        --user "$(id -u):$(id -g)" \
        "${LOG_DIR_ARGS[@]}" \
        "${GGUF_DIR_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$IMAGE_NAME" /app/scripts/entrypoint.sh
fi
