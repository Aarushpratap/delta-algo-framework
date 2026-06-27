#!/usr/bin/env bash
# deploy/start-streamlit.sh
# ─────────────────────────
# Wrapper executed by systemd as ExecStart.
#
# WHY THIS EXISTS:
#   systemd EnvironmentFile loads variables into the process environment, but
#   does NOT perform shell variable expansion inside ExecStart= — so
#   `--server.port=${DASHBOARD_PORT}` would be passed literally to Streamlit,
#   causing an argument-parse failure (exit status 2).
#
#   This script sources .env itself, resolves the port, and launches Streamlit
#   with the concrete value.  systemd still owns the process lifetime.
#
# DO NOT MODIFY trading logic here.

set -euo pipefail

PROJECT_ROOT="/home/rdpuser/delta-algo-framework"
ENV_FILE="$PROJECT_ROOT/.env"
VENV_STREAMLIT="$PROJECT_ROOT/.venv/bin/streamlit"
DASHBOARD="$PROJECT_ROOT/dashboard/app.py"

# Source .env to resolve variables
if [ -f "$ENV_FILE" ]; then
    # Export only KEY=VALUE lines; skip comments and blank lines
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Resolve port with a safe default
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"
LOG_LEVEL="${LOG_LEVEL:-info}"

exec "$VENV_STREAMLIT" run "$DASHBOARD" \
    --server.port="$DASHBOARD_PORT" \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --logger.level="$LOG_LEVEL"
