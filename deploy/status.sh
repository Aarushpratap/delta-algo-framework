#!/usr/bin/env bash
# deploy/status.sh
# ────────────────
# Display a comprehensive status overview for the Delta Algo framework.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env" 2>/dev/null || true; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

echo "============================================================"
echo "  Delta Algo Framework — Status"
echo "============================================================"

# Git info
echo ""
echo "[ Git ]"
cd "$PROJECT_ROOT"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "  Branch  : $BRANCH"
echo "  Commit  : $COMMIT"

# Service
echo ""
echo "[ Service: $SERVICE_NAME ]"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "  Status  : RUNNING"
else
    echo "  Status  : STOPPED"
fi

# Dashboard URL
echo ""
echo "[ Dashboard ]"
echo "  URL     : http://localhost:$DASHBOARD_PORT"

# Python
echo ""
echo "[ Python ]"
if [ -f "$VENV_DIR/bin/python" ]; then
    PY_VER=$("$VENV_DIR/bin/python" --version 2>&1)
    echo "  Version : $PY_VER"
    echo "  Venv    : ACTIVE ($VENV_DIR)"
else
    PY_VER=$(python3 --version 2>&1 || echo "unknown")
    echo "  Version : $PY_VER"
    echo "  Venv    : NOT FOUND"
fi

# Health
echo ""
echo "[ Health Check ]"
PYTHON_BIN="$VENV_DIR/bin/python"
[ -f "$PYTHON_BIN" ] || PYTHON_BIN="$(which python3)"
"$PYTHON_BIN" "$PROJECT_ROOT/healthcheck.py" 2>/dev/null || true

echo ""
echo "============================================================"
