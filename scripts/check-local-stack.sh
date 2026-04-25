#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PASS=0
WARN=0
FAIL=0

check() {
  local label="$1" ok="$2"
  if [ "$ok" = "true" ]; then
    echo "  [OK]   $label"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $label"
    FAIL=$((FAIL + 1))
  fi
}

warn() {
  local label="$1"
  echo "  [WARN] $label"
  WARN=$((WARN + 1))
}

echo "=== Local Stack Check ==="
echo ""

# Docker
if command -v docker &>/dev/null && docker info &>/dev/null; then
  check "Docker installed and running" "true"
else
  check "Docker installed and running" "false"
fi

# npm
if command -v npm &>/dev/null; then
  check "npm installed" "true"
else
  check "npm installed" "false"
fi

# auth-platform
if [ -f "$ROOT_DIR/auth-platform/docker-compose.yml" ]; then
  check "auth-platform/docker-compose.yml exists" "true"
else
  check "auth-platform/docker-compose.yml exists" "false"
fi

if [ -d "$ROOT_DIR/auth-platform/.venv" ]; then
  check "auth-platform/.venv exists" "true"
else
  warn "auth-platform/.venv missing (needed for make test/lint)"
fi

# capture-workbench
if [ -f "$ROOT_DIR/capture-workbench/package.json" ]; then
  check "capture-workbench/package.json exists" "true"
else
  check "capture-workbench/package.json exists" "false"
fi

if [ -d "$ROOT_DIR/capture-workbench/node_modules" ]; then
  check "capture-workbench/node_modules installed" "true"
else
  warn "capture-workbench/node_modules missing (run: cd capture-workbench && npm install)"
fi

# Backend health (only if containers appear running)
echo ""
if docker compose -f "$ROOT_DIR/auth-platform/docker-compose.yml" ps --status running 2>/dev/null | grep -q "auth-platform"; then
  echo "  Backend containers detected. Checking health..."
  cd "$ROOT_DIR/auth-platform"
  if make health 2>/dev/null; then
    check "Backend health check" "true"
  else
    check "Backend health check" "false"
  fi
else
  warn "Backend containers not running (run: make backend-up)"
fi

echo ""
echo "=== Summary: $PASS passed, $WARN warnings, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
