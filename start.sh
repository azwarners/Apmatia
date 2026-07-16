#!/bin/bash

# Apmatia Docker startup script
# Usage: ./start.sh [core|streamlit|dev]
#   core     - Start the Apmatia core container on localhost:8000 (default)
#   streamlit - Start the Streamlit interface container
#   dev      - Start both the core and Streamlit containers

set -e

MODE="core"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
CORE_IMAGE_NAME="apmatia"
STREAMLIT_IMAGE_NAME="apmatia-streamlit"
CORE_CONTAINER_NAME="apmatia"
STREAMLIT_CONTAINER_NAME="apmatia-streamlit"

for arg in "$@"; do
    case "$arg" in
        core|streamlit|dev)
            MODE="$arg"
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./start.sh [core|streamlit|dev]"
            exit 1
            ;;
    esac
done

IMAGE_NAME="$CORE_IMAGE_NAME"
if [ "$MODE" = "streamlit" ]; then
    IMAGE_NAME="$STREAMLIT_IMAGE_NAME"
fi

build_image() {
    local image_name="$1"
    local build_mode="$2"
    local build_message="$3"

    echo "$build_message"
    docker build -t "$image_name" --build-arg MODE="$build_mode" .
}

if [ "$MODE" = "core" ]; then
    build_image "$CORE_IMAGE_NAME" "core" "Building Apmatia core container..."
elif [ "$MODE" = "streamlit" ]; then
    build_image "$STREAMLIT_IMAGE_NAME" "streamlit" "Building Apmatia Streamlit interface container..."
elif [ "$MODE" = "dev" ]; then
    build_image "$CORE_IMAGE_NAME" "core" "Building Apmatia core container..."
    build_image "$STREAMLIT_IMAGE_NAME" "streamlit" "Building Apmatia Streamlit interface container..."
else
    echo "Unknown mode: $MODE"
    echo "Usage: ./start.sh [core|streamlit|dev]"
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

build_runtime_args() {
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
}

stop_container_if_exists() {
    local container_name="$1"

    if docker ps -a --format '{{.Names}}' | grep -q "^$container_name$"; then
        echo "Stopping existing container..."
        docker stop "$container_name"
        docker rm "$container_name"
    fi
}

run_core_container() {
    local image_name="$1"

    build_runtime_args
    docker run \
        --name "$CORE_CONTAINER_NAME" \
        -p 127.0.0.1:8000:8000 \
        -v "$REPO_ROOT":/app \
        -v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR" \
        -v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR" \
        -v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR" \
        -v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR" \
        -e HOME="$APMATIA_CONTAINER_HOME" \
        -e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR" \
        -e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR" \
        -e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules" \
        -e APMATIA_SERVER_HOST=0.0.0.0 \
        -e APMATIA_SERVER_TRANSPORT_SECURITY_CONTAINER_HOST_LOOPBACK_ONLY=true \
        --user "$(id -u):$(id -g)" \
        "${LOG_DIR_ARGS[@]}" \
        "${GGUF_DIR_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$image_name" /app/scripts/entrypoint.sh
}

run_core_container_detached() {
    local image_name="$1"

    build_runtime_args
    docker run -d \
        --name "$CORE_CONTAINER_NAME" \
        -p 127.0.0.1:8000:8000 \
        -v "$REPO_ROOT":/app \
        -v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR" \
        -v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR" \
        -v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR" \
        -v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR" \
        -e HOME="$APMATIA_CONTAINER_HOME" \
        -e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR" \
        -e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR" \
        -e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules" \
        -e APMATIA_SERVER_HOST=0.0.0.0 \
        -e APMATIA_SERVER_TRANSPORT_SECURITY_CONTAINER_HOST_LOOPBACK_ONLY=true \
        --user "$(id -u):$(id -g)" \
        "${LOG_DIR_ARGS[@]}" \
        "${GGUF_DIR_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$image_name" /app/scripts/entrypoint.sh
}

run_streamlit_container() {
    local image_name="$1"

    build_runtime_args
    docker run \
        --name "$STREAMLIT_CONTAINER_NAME" \
        -p 127.0.0.1:8501:8501 \
        -v "$REPO_ROOT":/app \
        -v "$APMATIA_WORKSPACE_DIR_HOST":"$APMATIA_CONTAINER_WORKSPACE_DIR" \
        -v "$APMATIA_HOME_HOST":"$APMATIA_CONTAINER_HOME_DIR" \
        -v "$APMATIA_CONFIG_DIR_HOST":"$APMATIA_CONTAINER_CONFIG_DIR" \
        -v "$APMATIA_DATA_DIR_HOST":"$APMATIA_CONTAINER_DATA_DIR" \
        -e HOME="$APMATIA_CONTAINER_HOME" \
        -e APMATIA_HOME="$APMATIA_CONTAINER_HOME_DIR" \
        -e APMATIA_DATA_DIR="$APMATIA_CONTAINER_DATA_DIR" \
        -e APMATIA_WORKSPACE_ROOT="$APMATIA_CONTAINER_WORKSPACE_DIR/modules" \
        -e APMATIA_STREAMLIT_HOST=0.0.0.0 \
        -e APMATIA_SERVER_TRANSPORT_SECURITY_CONTAINER_HOST_LOOPBACK_ONLY=true \
        --user "$(id -u):$(id -g)" \
        "${LOG_DIR_ARGS[@]}" \
        "${GGUF_DIR_ARGS[@]}" \
        --entrypoint /bin/bash \
        "$image_name" /app/scripts/entrypoint.sh
}

run_dev_mode() {
    cleanup_dev_mode() {
        docker stop "$CORE_CONTAINER_NAME" >/dev/null 2>&1 || true
        docker stop "$STREAMLIT_CONTAINER_NAME" >/dev/null 2>&1 || true
    }

    trap cleanup_dev_mode EXIT INT TERM

    stop_container_if_exists "$CORE_CONTAINER_NAME"
    stop_container_if_exists "$STREAMLIT_CONTAINER_NAME"

    echo "Starting $CORE_CONTAINER_NAME and $STREAMLIT_CONTAINER_NAME..."
    run_core_container_detached "$CORE_IMAGE_NAME" >/dev/null
    run_streamlit_container "$STREAMLIT_IMAGE_NAME"
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

ensure_host_permissions "$APMATIA_HOME_HOST" "$APMATIA_CONTAINER_HOME_DIR"
ensure_host_permissions "$APMATIA_DATA_DIR_HOST" "$APMATIA_CONTAINER_DATA_DIR"
ensure_host_permissions "$APMATIA_CONFIG_DIR_HOST" "$APMATIA_CONTAINER_CONFIG_DIR"
mkdir -p "$APMATIA_WORKSPACE_ROOT_HOST"
if [ -n "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST" ]; then
    mkdir -p "$APMATIA_LLAMA_SERVER_LOG_DIR_HOST"
fi

# Run the container
if [ "$MODE" = "dev" ]; then
    run_dev_mode
elif [ "$MODE" = "streamlit" ]; then
    stop_container_if_exists "$STREAMLIT_CONTAINER_NAME"
    echo "Starting $STREAMLIT_CONTAINER_NAME..."
    run_streamlit_container "$STREAMLIT_IMAGE_NAME"
else
    stop_container_if_exists "$CORE_CONTAINER_NAME"
    echo "Starting $CORE_CONTAINER_NAME..."
    run_core_container "$CORE_IMAGE_NAME"
fi
