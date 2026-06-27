#!/usr/bin/env bash
# deploy/doctor.sh
# ────────────────
# Deep system diagnostics for the Delta Algo framework.
# Checks every dependency, file, and credential without making API calls.
#
# Usage:
#   bash deploy/doctor.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# Load .env silently so we can inspect values without printing them
# shellcheck disable=SC1091
set -a; source "$PROJECT_ROOT/.env" 2>/dev/null || true; set +a

GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
RESET="\033[0m"
BOLD="\033[1m"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() { echo -e "  ${GREEN}[PASS]${RESET}  $1"; ((PASS_COUNT++)); }
fail() { echo -e "  ${RED}[FAIL]${RESET}  $1"; ((FAIL_COUNT++)); }
warn() { echo -e "  ${YELLOW}[WARN]${RESET}  $1"; ((WARN_COUNT++)); }

echo ""
echo -e "${BOLD}============================================================${RESET}"
echo -e "${BOLD}  Delta Algo Framework — Doctor${RESET}"
echo -e "${BOLD}  Project: $PROJECT_ROOT${RESET}"
echo -e "${BOLD}============================================================${RESET}"

# ── 1. .env ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Configuration ]${RESET}"
if [ -f "$PROJECT_ROOT/.env" ]; then
    pass ".env file exists"
else
    fail ".env file not found — run: cp .env.example .env"
fi

if [ -f "$PROJECT_ROOT/config/settings.py" ]; then
    pass "config/settings.py exists"
else
    fail "config/settings.py missing"
fi

# ── 2. Credentials ───────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ API Credentials ]${RESET}"
API_KEY="${DELTA_API_KEY:-}"
API_SECRET="${DELTA_API_SECRET:-}"

if [ -n "$API_KEY" ] && [ "$API_KEY" != "your_api_key_here" ]; then
    pass "DELTA_API_KEY is set"
else
    fail "DELTA_API_KEY is missing or is still the placeholder value"
fi

if [ -n "$API_SECRET" ] && [ "$API_SECRET" != "your_api_secret_here" ]; then
    pass "DELTA_API_SECRET is set"
else
    fail "DELTA_API_SECRET is missing or is still the placeholder value"
fi

# ── 3. Virtual environment ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Virtual Environment ]${RESET}"
if [ -d "$VENV_DIR" ]; then
    pass "venv directory exists: $VENV_DIR"
else
    fail "venv not found at $VENV_DIR — run: bash deploy/install.sh"
fi

if [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PY_VER=$("$VENV_DIR/bin/python" --version 2>&1)
    pass "venv Python: $VENV_PY_VER"
else
    fail "venv Python binary not found"
fi

# ── 4. Python packages ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Required Packages ]${RESET}"
PYTHON_BIN="$VENV_DIR/bin/python"
[ -f "$PYTHON_BIN" ] || PYTHON_BIN="$(which python3)"

check_pkg() {
    local module="$1"
    local label="${2:-$1}"
    if "$PYTHON_BIN" -c "import $module" 2>/dev/null; then
        pass "$label installed"
    else
        fail "$label NOT installed — run: pip install $label"
    fi
}

check_pkg dotenv   "python-dotenv"
check_pkg requests "requests"
check_pkg streamlit "streamlit"
check_pkg plotly   "plotly"
check_pkg pandas   "pandas"

# ── 5. Project structure ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Project Structure ]${RESET}"
REQUIRED_DIRS=(
    "config" "core" "exchange" "feeds" "indicators"
    "strategy" "risk" "safety" "backtest" "paper"
    "replay" "live" "dashboard" "deploy" "logs"
)
for d in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$d" ]; then
        pass "directory: $d/"
    else
        fail "directory missing: $d/"
    fi
done

# ── 6. Key files ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Key Files ]${RESET}"
REQUIRED_FILES=(
    "dashboard/app.py"
    "healthcheck.py"
    "requirements.txt"
    ".env.example"
    "main.py"
)
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$f" ]; then
        pass "$f"
    else
        fail "$f not found"
    fi
done

# ── 7. File permissions ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Permissions ]${RESET}"
SCRIPTS=(
    "deploy/install.sh" "deploy/deploy.sh" "deploy/start.sh"
    "deploy/stop.sh" "deploy/restart.sh" "deploy/status.sh"
    "deploy/update.sh" "deploy/doctor.sh" "deploy/logs.sh"
    "deploy/backup.sh" "deploy/rollback.sh"
)
for s in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$PROJECT_ROOT/$s"
    if [ -f "$SCRIPT_PATH" ]; then
        if [ -x "$SCRIPT_PATH" ]; then
            pass "$s is executable"
        else
            warn "$s exists but is not executable — run: chmod +x $s"
        fi
    fi
done

# ── 8. Logs directory writable ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[ Logs ]${RESET}"
if [ -d "$PROJECT_ROOT/logs" ]; then
    if [ -w "$PROJECT_ROOT/logs" ]; then
        pass "logs/ directory is writable"
    else
        fail "logs/ directory is not writable"
    fi
else
    warn "logs/ directory does not exist — run: mkdir -p logs"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}------------------------------------------------------------${RESET}"
TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}All checks passed ($PASS_COUNT/$TOTAL) — Framework is ready.${RESET}"
else
    echo -e "  ${RED}${BOLD}$FAIL_COUNT check(s) FAILED ($PASS_COUNT passed, $WARN_COUNT warnings)${RESET}"
    echo -e "  ${RED}Fix the issues above before deploying.${RESET}"
fi
echo -e "${BOLD}============================================================${RESET}"
echo ""

exit "$FAIL_COUNT"
