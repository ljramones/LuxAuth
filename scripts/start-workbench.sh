#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Starting capture-workbench ==="
cd "$ROOT_DIR/capture-workbench"

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "Copying .env.example to .env"
  cp .env.example .env
fi

echo ""
echo "Starting Vite dev server..."
echo "  Local: http://localhost:5173"
echo ""
exec npm run dev
