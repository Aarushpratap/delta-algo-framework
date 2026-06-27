#!/usr/bin/env bash
# deploy/start.sh
# ───────────────
# Start the Delta Algo service via systemd.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load service name and port from .env
# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env"; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

echo "Starting $SERVICE_NAME..."
sudo systemctl start "$SERVICE_NAME"
sleep 2
sudo systemctl status "$SERVICE_NAME" --no-pager -l

echo ""
echo "Dashboard: http://localhost:$DASHBOARD_PORT"
