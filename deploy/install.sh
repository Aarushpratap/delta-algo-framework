#!/usr/bin/env bash
# deploy/install.sh
# ─────────────────
# One-time installation script for the Delta Algo trading framework.
# Safe to re-run: idempotent on all steps.
# Includes pre-flight validation of the systemd service unit.
#
# Usage:
#   bash deploy/install.sh

set -euo pipefail

# ── Resolve project root from script location ────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
LOGS_DIR="$PROJECT_ROOT/logs"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
SERVICE_FILE="$PROJECT_ROOT/systemd/delta-algo.service"
START_WRAPPER="$PROJECT_ROOT/deploy/start-streamlit.sh"
DASHBOARD="$PROJECT_ROOT/dashboard/app.py"

echo "============================================================"
echo "  Delta Algo Framework — Installation"
echo "  Project: $PROJECT_ROOT"
echo "============================================================"

# 1. Verify Python >= 3.10
echo ""
echo "[1/7] Verifying Python version..."
PYTHON_BIN="$(which python3 2>/dev/null || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo "  [FAIL] python3 not found on PATH. Please install Python 3.10+."
    exit 1
fi
PY_VERSION=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "  [FAIL] Python $PY_VERSION found — 3.10+ required."
    exit 1
fi
echo "  [PASS] Python $PY_VERSION"

# 2. Create virtual environment if missing
echo ""
echo "[2/7] Verifying virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "  [DONE] Virtual environment created."
else
    echo "  [PASS] Virtual environment already exists."
fi

# 3. Activate venv and install requirements
echo ""
echo "[3/7] Installing requirements..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$REQUIREMENTS" --quiet
echo "  [DONE] All packages installed."

# 4. Create logs directory
echo ""
echo "[4/7] Creating logs directory..."
mkdir -p "$LOGS_DIR"
echo "  [PASS] $LOGS_DIR"

# 5. Verify .env exists
echo ""
echo "[5/7] Checking .env configuration..."
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "  [FAIL] .env not found. Create it from the template:"
    echo ""
    echo "    cp \"$ENV_EXAMPLE\" \"$ENV_FILE\""
    echo "    nano \"$ENV_FILE\"   # fill in DELTA_API_KEY and DELTA_API_SECRET"
    echo ""
    exit 1
fi
echo "  [PASS] .env found."

# 6. Validate systemd service unit and dependencies
echo ""
echo "[6/7] Validating systemd service and dependencies..."
VALIDATION_FAILED=0

# 6a. systemd syntax check (requires systemd-analyze on the host)
if command -v systemd-analyze &>/dev/null; then
    if systemd-analyze verify "$SERVICE_FILE" 2>/dev/null; then
        echo "  [PASS] systemd service syntax valid."
    else
        echo "  [WARN] systemd-analyze reported warnings for $SERVICE_FILE — check manually."
    fi
else
    echo "  [SKIP] systemd-analyze not available on this system."
fi

# 6b. Verify the ExecStart wrapper script exists
if [ -f "$START_WRAPPER" ]; then
    echo "  [PASS] ExecStart wrapper exists: deploy/start-streamlit.sh"
else
    echo "  [FAIL] ExecStart wrapper NOT found: $START_WRAPPER"
    VALIDATION_FAILED=1
fi

# 6c. Verify Streamlit executable exists inside venv
STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
if [ -f "$STREAMLIT_BIN" ]; then
    STREAMLIT_VER=$("$STREAMLIT_BIN" --version 2>&1 | head -1)
    echo "  [PASS] Streamlit executable: $STREAMLIT_BIN ($STREAMLIT_VER)"
else
    echo "  [FAIL] Streamlit NOT found at $STREAMLIT_BIN — did pip install succeed?"
    VALIDATION_FAILED=1
fi

# 6d. Verify dashboard entry point exists
if [ -f "$DASHBOARD" ]; then
    echo "  [PASS] Dashboard file: dashboard/app.py"
else
    echo "  [FAIL] Dashboard file NOT found: $DASHBOARD"
    VALIDATION_FAILED=1
fi

# Make all deploy scripts executable
chmod +x "$PROJECT_ROOT"/deploy/*.sh
echo "  [PASS] All deploy/ scripts are executable."

if [ "$VALIDATION_FAILED" -ne 0 ]; then
    echo ""
    echo "  [FAIL] Validation step failed. Fix the issues above before deploying."
    exit 1
fi

# 7. Run healthcheck
echo ""
echo "[7/7] Running pre-flight health check..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/healthcheck.py" || {
    echo ""
    echo "  [WARN] Health check reported failures. Fix them before starting the bot."
}

echo ""
echo "============================================================"
echo "  Installation complete!"
echo ""
echo "  Next steps:"
echo "    sudo cp systemd/delta-algo.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable delta-algo"
echo "    bash deploy/start.sh"
echo "============================================================"
