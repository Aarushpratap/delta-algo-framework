#!/usr/bin/env bash
# deploy/status.sh
# ────────────────
# Display a comprehensive status overview for the Delta Algo framework.
# Shows: service state, PID, listening port, dashboard URL, last restart time,
# Python version, venv state, and an inline health summary.

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

# ── Git ───────────────────────────────────────────────────────────────────────
echo ""
echo "[ Git ]"
cd "$PROJECT_ROOT"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "  Branch       : $BRANCH"
echo "  Commit       : $COMMIT"

# ── Service ───────────────────────────────────────────────────────────────────
echo ""
echo "[ Service: $SERVICE_NAME ]"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    SVC_STATE="RUNNING"

    # PID of the main process
    SVC_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null || echo "unknown")

    # Last active (start) time
    ACTIVE_SINCE=$(systemctl show -p ActiveEnterTimestamp --value "$SERVICE_NAME" 2>/dev/null || echo "unknown")

    # Actual listening port — look for the port in ss output
    LISTENING_PORT=$(ss -tlnp 2>/dev/null \
        | awk -v svc="$SERVICE_NAME" '/LISTEN/ && NR>1 {print $4}' \
        | grep -oP ':\K\d+$' \
        | head -1 || echo "$DASHBOARD_PORT (configured)")

    echo "  State        : $SVC_STATE"
    echo "  PID          : $SVC_PID"
    echo "  Listening    : $LISTENING_PORT"
    echo "  Last Start   : $ACTIVE_SINCE"
else
    echo "  State        : STOPPED"
    echo "  PID          : -"
    echo "  Listening    : -"
    LAST_INACTIVE=$(systemctl show -p InactiveEnterTimestamp --value "$SERVICE_NAME" 2>/dev/null || echo "unknown")
    echo "  Last Stop    : $LAST_INACTIVE"
fi

# ── Dashboard ─────────────────────────────────────────────────────────────────
echo ""
echo "[ Dashboard ]"
echo "  URL          : http://localhost:$DASHBOARD_PORT"

# ── Python ────────────────────────────────────────────────────────────────────
echo ""
echo "[ Python ]"
if [ -f "$VENV_DIR/bin/python" ]; then
    PY_VER=$("$VENV_DIR/bin/python" --version 2>&1)
    echo "  Version      : $PY_VER"
    echo "  Venv         : ACTIVE ($VENV_DIR)"
    PYTHON_BIN="$VENV_DIR/bin/python"
else
    PY_VER=$(python3 --version 2>&1 || echo "unknown")
    echo "  Version      : $PY_VER"
    echo "  Venv         : NOT FOUND"
    PYTHON_BIN="$(which python3 2>/dev/null || echo python3)"
fi

# ── Health Check ──────────────────────────────────────────────────────────────
echo ""
echo "[ Health Check ]"
"$PYTHON_BIN" "$PROJECT_ROOT/healthcheck.py" --quiet 2>/dev/null || true

echo ""
echo "============================================================"
