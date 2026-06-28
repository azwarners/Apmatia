#!/bin/bash
set -euo pipefail

# Stop both HTTP API and Streamlit containers
docker compose down --remove-orphans
