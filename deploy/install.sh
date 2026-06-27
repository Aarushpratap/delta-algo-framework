#!/usr/bin/env bash
# deploy/install.sh
# ─────────────────
# One-time installation script for the Delta Algo trading framework.
# Safe to re-run: idempotent on all steps.
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

echo "============================================================"
echo "  Delta Algo Framework — Installation"
echo "  Project: $PROJECT_ROOT"
echo "============================================================"

# 1. Verify Python ≥ 3.10
echo ""
echo "[1/6] Verifying Python version..."
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
echo "[2/6] Verifying virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "  [DONE] Virtual environment created."
else
    echo "  [PASS] Virtual environment already exists."
fi

# 3. Activate venv and install requirements
echo ""
echo "[3/6] Installing requirements..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$REQUIREMENTS" --quiet
echo "  [DONE] All packages installed."

# 4. Create logs directory
echo ""
echo "[4/6] Creating logs directory..."
mkdir -p "$LOGS_DIR"
echo "  [PASS] $LOGS_DIR"

# 5. Verify .env exists
echo ""
echo "[5/6] Checking .env configuration..."
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "  [FAIL] .env not found. Create it from the template:"
    echo ""
    echo "    cp \"$ENV_EXAMPLE\" \"$ENV_FILE\""
    echo "    nano \"$ENV_FILE\"   # fill in DELTA_API_KEY and DELTA_API_SECRET"
    echo ""
    exit 1
fi
echo "  [PASS] .env found at $ENV_FILE"

# 6. Run healthcheck
echo ""
echo "[6/6] Running pre-flight health check..."
"$VENV_DIR/bin/python" "$PROJECT_ROOT/healthcheck.py" || {
    echo ""
    echo "  [WARN] Health check reported failures. Fix them before starting the bot."
}

echo ""
echo "============================================================"
echo "  Installation complete!"
echo ""
echo "  Start the dashboard:"
echo "    bash deploy/start.sh"
echo ""
echo "  Or run directly:"
echo "    streamlit run dashboard/app.py"
echo "============================================================"
