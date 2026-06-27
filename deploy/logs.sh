#!/usr/bin/env bash
# deploy/logs.sh
# ──────────────
# Stream live journal logs from the Delta Algo service.
#
# Usage:
#   bash deploy/logs.sh           # follow live (default)
#   bash deploy/logs.sh --tail 50 # show last 50 lines then exit

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env" 2>/dev/null || true; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"

echo "Streaming logs for: $SERVICE_NAME"
echo "Press Ctrl+C to stop."
echo "----------------------------------------"

# Pass any extra arguments (e.g. --tail 100) directly to journalctl
journalctl -u "$SERVICE_NAME" -f "$@"
