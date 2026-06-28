#!/bin/bash

set -e

IMAGE_NAME="apmatia-test"
CONTAINER_NAME="apmatia-test"

echo "Building test container..."
docker build -f Dockerfile -t "$IMAGE_NAME" .

echo "Running tests in container..."
docker run --rm --name "$CONTAINER_NAME" "$IMAGE_NAME" pytest tests/unit/ tests/integration/
