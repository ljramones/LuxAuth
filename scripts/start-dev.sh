#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting full local dev environment ==="
echo ""

# Start backend first
"$SCRIPT_DIR/start-backend.sh"

echo ""
echo "=== Backend is up. Starting workbench... ==="
echo ""

# Start workbench in foreground
exec "$SCRIPT_DIR/start-workbench.sh"
