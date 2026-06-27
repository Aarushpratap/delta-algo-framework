#!/usr/bin/env bash
# deploy/backup.sh
# ────────────────
# Create a timestamped backup of the project before deployment.
# Backs up: code (excluding .venv, __pycache__, .git), .env (encrypted name),
# and the logs directory metadata.
#
# Backups are stored in: $PROJECT_ROOT/backups/
# They are NEVER automatically deleted.
#
# Usage:
#   bash deploy/backup.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="delta-algo_backup_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

echo "============================================================"
echo "  Delta Algo Framework — Backup"
echo "  Timestamp : $TIMESTAMP"
echo "  Output    : $BACKUP_PATH"
echo "============================================================"

# Create backups directory (never delete it)
mkdir -p "$BACKUP_DIR"

# Exclude large / ephemeral directories
tar -czf "$BACKUP_PATH" \
    -C "$PROJECT_ROOT" \
    --exclude=".venv" \
    --exclude="__pycache__" \
    --exclude=".git" \
    --exclude=".pytest_cache" \
    --exclude="*.pyc" \
    --exclude="backups" \
    .

SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
echo ""
echo "  [DONE] Backup created: $BACKUP_PATH ($SIZE)"

# Write a pointer to the latest backup for rollback
echo "$BACKUP_PATH" > "$BACKUP_DIR/latest.txt"
echo "  [INFO] Latest backup pointer updated."
echo "============================================================"
