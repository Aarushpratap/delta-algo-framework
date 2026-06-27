#!/usr/bin/env bash
# deploy/rollback.sh
# ──────────────────
# Restore the most recent backup created by backup.sh.
# Stops the service, restores files, then restarts.
#
# SAFETY: Never overwrites .env — the live credentials are preserved.
# SAFETY: Never deletes the backup archive after restoring.
#
# Usage:
#   bash deploy/rollback.sh               # restores the latest backup
#   bash deploy/rollback.sh <backup.tar.gz>  # restores a specific archive

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
LATEST_FILE="$BACKUP_DIR/latest.txt"

# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env" 2>/dev/null || true; set +a
SERVICE_NAME="${SERVICE_NAME:-delta-algo}"

echo "============================================================"
echo "  Delta Algo Framework — Rollback"
echo "============================================================"

# Determine which archive to restore
if [ -n "${1:-}" ]; then
    ARCHIVE="$1"
else
    if [ ! -f "$LATEST_FILE" ]; then
        echo "  [FAIL] No backup pointer found at $LATEST_FILE"
        echo "         Run bash deploy/backup.sh first, or pass a specific archive."
        exit 1
    fi
    ARCHIVE=$(cat "$LATEST_FILE")
fi

if [ ! -f "$ARCHIVE" ]; then
    echo "  [FAIL] Archive not found: $ARCHIVE"
    exit 1
fi

ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo "  Archive : $ARCHIVE ($ARCHIVE_SIZE)"
echo ""
read -rp "  Proceed with rollback? This will overwrite code files. [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "  Rollback cancelled."
    exit 0
fi

# 1. Stop the service
echo ""
echo "[1/4] Stopping service..."
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
echo "  [DONE]"

# 2. Back up the current .env so it is never lost
ENV_BACKUP="$BACKUP_DIR/.env.pre_rollback_$(date +%Y%m%d_%H%M%S)"
cp "$PROJECT_ROOT/.env" "$ENV_BACKUP" 2>/dev/null || true
echo "[2/4] Current .env preserved at $ENV_BACKUP"

# 3. Extract the archive (exclude .env so we don't overwrite live credentials)
echo "[3/4] Extracting archive..."
tar -xzf "$ARCHIVE" \
    -C "$PROJECT_ROOT" \
    --exclude=".env"
echo "  [DONE] Files restored."

# 4. Restart the service
echo "[4/4] Restarting service..."
sudo systemctl start "$SERVICE_NAME" 2>/dev/null || true
sleep 2

echo ""
echo "============================================================"
echo "  Rollback complete!"
echo "  Archive  : $ARCHIVE"
echo "  Service  : $(systemctl is-active $SERVICE_NAME 2>/dev/null || echo unknown)"
echo "  NOTE: .env was NOT overwritten. Your credentials are safe."
echo "============================================================"
