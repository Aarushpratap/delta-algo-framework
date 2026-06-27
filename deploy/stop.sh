#!/usr/bin/env bash
# deploy/stop.sh
# ──────────────
# Stop the Delta Algo service via systemd.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env"; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"

echo "Stopping $SERVICE_NAME..."
sudo systemctl stop "$SERVICE_NAME"
echo "Service stopped."
