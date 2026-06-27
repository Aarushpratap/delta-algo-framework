#!/usr/bin/env bash
# deploy/deploy.sh
# ────────────────
# Deploy latest code changes to a running server.
# Only installs new packages if requirements.txt has changed.
#
# Usage:
#   bash deploy/deploy.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
REQUIREMENTS_HASH_FILE="$PROJECT_ROOT/.requirements.md5"

# Load .env to get SERVICE_NAME and DASHBOARD_PORT
# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env"; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

echo "============================================================"
echo "  Delta Algo Framework — Deployment"
echo "  Service : $SERVICE_NAME"
echo "  Project : $PROJECT_ROOT"
echo "============================================================"

# 1. Backup before deploy
echo ""
echo "[1/5] Creating backup..."
bash "$PROJECT_ROOT/deploy/backup.sh"

# 2. Git pull
echo ""
echo "[2/5] Pulling latest code..."
cd "$PROJECT_ROOT"
git pull
COMMIT=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  Branch : $BRANCH"
echo "  Commit : $COMMIT"

# 3. Activate venv; install new packages only if requirements changed
echo ""
echo "[3/5] Checking dependencies..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
NEW_HASH=$(md5sum "$REQUIREMENTS" | awk '{print $1}')
OLD_HASH=""
[ -f "$REQUIREMENTS_HASH_FILE" ] && OLD_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
if [ "$NEW_HASH" != "$OLD_HASH" ]; then
    echo "  requirements.txt changed — installing updates..."
    pip install -r "$REQUIREMENTS" --quiet
    echo "$NEW_HASH" > "$REQUIREMENTS_HASH_FILE"
    echo "  [DONE] Dependencies updated."
else
    echo "  [SKIP] requirements.txt unchanged — skipping pip install."
fi

# 4. Run healthcheck
echo ""
echo "[4/5] Running health check..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/healthcheck.py" || {
    echo ""
    echo "  [WARN] Health check failures detected. Review above before proceeding."
}

# 5. Restart service
echo ""
echo "[5/5] Restarting service..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl restart "$SERVICE_NAME"
    echo "  [DONE] $SERVICE_NAME restarted."
else
    sudo systemctl start "$SERVICE_NAME"
    echo "  [DONE] $SERVICE_NAME started (was not running)."
fi

echo ""
echo "============================================================"
echo "  Deployment complete!"
echo "  Branch    : $BRANCH"
echo "  Commit    : $COMMIT"
echo "  Service   : $(systemctl is-active $SERVICE_NAME 2>/dev/null || echo unknown)"
echo "  Dashboard : http://localhost:$DASHBOARD_PORT"
echo "============================================================"
