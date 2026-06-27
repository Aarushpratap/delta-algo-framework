#!/usr/bin/env bash
# deploy/start.sh
# ───────────────
# Start the Delta Algo service via systemd with automatic failure diagnostics.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load service name and port from .env
# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env"; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

echo "Starting $SERVICE_NAME..."
sudo systemctl start "$SERVICE_NAME"

# Wait briefly and check if the service actually came up
sleep 3

if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "  [OK] Service is running."
    echo "  Dashboard : http://localhost:$DASHBOARD_PORT"
else
    echo ""
    echo "  [FAIL] Service failed to start. Collecting diagnostics..."
    echo ""
    echo "──────────────────────────────────────────────────────"
    echo "  systemctl status $SERVICE_NAME"
    echo "──────────────────────────────────────────────────────"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l || true
    echo ""
    echo "──────────────────────────────────────────────────────"
    echo "  journalctl -u $SERVICE_NAME -n 50 --no-pager"
    echo "──────────────────────────────────────────────────────"
    sudo journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true
    echo ""
    echo "  Tip: Check that .env is correctly configured and"
    echo "       bash deploy/doctor.sh passes all checks."
    exit 1
fi
