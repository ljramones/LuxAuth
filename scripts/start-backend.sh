#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Starting auth-platform backend ==="
cd "$ROOT_DIR/auth-platform"

docker compose up --build -d

echo ""
echo "Waiting for services to start..."
sleep 8

echo ""
echo "=== Running health check ==="
if make health; then
  echo ""
  echo "=== Backend services ==="
  echo "  device-service:          http://localhost:8103"
  echo "  capture-intake-service:  http://localhost:8106"
  echo "  image-quality-service:   http://localhost:8201"
  echo "  normalization-service:   http://localhost:8202"
  echo "  (all services: make health from auth-platform/)"
  echo ""
  echo "Backend is ready."
else
  echo ""
  echo "=== Health check failed ==="
  echo "Troubleshooting:"
  echo "  cd auth-platform"
  echo "  docker compose ps"
  echo "  docker compose logs -f"
  echo "  make health"
  exit 1
fi
