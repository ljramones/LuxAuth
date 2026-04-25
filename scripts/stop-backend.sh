#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Stopping auth-platform backend ==="
cd "$ROOT_DIR/auth-platform"

docker compose stop

echo ""
echo "Containers stopped. Volumes preserved."
echo "To delete volumes and reset data: cd auth-platform && make down"
