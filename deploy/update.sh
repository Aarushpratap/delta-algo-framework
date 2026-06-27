#!/usr/bin/env bash
# deploy/update.sh
# ────────────────
# One-command full update pipeline.
# Runs: backup → git pull → pip install (if needed) → doctor → restart → status
#
# Usage:
#   bash deploy/update.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
REQUIREMENTS_HASH_FILE="$PROJECT_ROOT/.requirements.md5"

# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env" 2>/dev/null || true; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

echo "============================================================"
echo "  Delta Algo Framework — One-Command Update"
echo "============================================================"

# Step 1: Backup
echo ""
echo "[Step 1/5] Creating backup..."
bash "$PROJECT_ROOT/deploy/backup.sh"

# Step 2: Git pull
echo ""
echo "[Step 2/5] Pulling latest code..."
cd "$PROJECT_ROOT"
git pull
COMMIT=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  Branch : $BRANCH"
echo "  Commit : $COMMIT"

# Step 3: Install packages if requirements changed
echo ""
echo "[Step 3/5] Checking dependencies..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
NEW_HASH=$(md5sum "$REQUIREMENTS" | awk '{print $1}')
OLD_HASH=""
[ -f "$REQUIREMENTS_HASH_FILE" ] && OLD_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
if [ "$NEW_HASH" != "$OLD_HASH" ]; then
    echo "  requirements.txt changed — installing updates..."
    pip install -r "$REQUIREMENTS" --quiet
    echo "$NEW_HASH" > "$REQUIREMENTS_HASH_FILE"
    echo "  [DONE]"
else
    echo "  [SKIP] Dependencies unchanged."
fi

# Step 4: Doctor
echo ""
echo "[Step 4/5] Running doctor..."
bash "$PROJECT_ROOT/deploy/doctor.sh" || {
    echo ""
    echo "  [WARN] Doctor reported failures. Review above before proceeding."
}

# Step 5: Restart
echo ""
echo "[Step 5/5] Restarting service..."
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    sudo systemctl restart "$SERVICE_NAME"
else
    sudo systemctl start "$SERVICE_NAME"
fi
sleep 2

echo ""
echo "============================================================"
echo "  Update complete!"
echo "  Branch    : $BRANCH"
echo "  Commit    : $COMMIT"
echo "  Service   : $(systemctl is-active $SERVICE_NAME 2>/dev/null || echo unknown)"
echo "  Dashboard : http://localhost:$DASHBOARD_PORT"
echo "============================================================"

# Final detailed status
bash "$PROJECT_ROOT/deploy/status.sh"
