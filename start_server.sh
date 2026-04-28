#!/bin/bash

# NITK Academic Advisor — Server Startup Script

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status()  { echo -e "${BLUE}[INFO]${NC}    $1"; }
print_success() { echo -e "${GREEN}[OK]${NC}      $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC}    $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC}   $1"; }
print_step()    { echo -e "${CYAN}[STEP]${NC}    $1"; }

# ── Locate project ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
cd "$PROJECT_DIR"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   NITK Academic Advisor — Starting Up${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Load .env ─────────────────────────────────────────────────────────────────
if [ -f ".env" ]; then
    print_status "Loading .env..."
    while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }"           ]] && continue
        [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]] && export "$line"
    done < .env
fi

# Resolve ports after .env is loaded
export API_HOST=${API_HOST:-"127.0.0.1"}
export API_PORT=${API_PORT:-8000}
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

# ── Kill ALL old processes (by name AND by port) ──────────────────────────────
print_step "Cleaning up old processes..."

# Kill any process whose command line contains 'uvicorn src.api.main' or 'uvicorn backend.src.api.main'
OLD_PIDS=$(pgrep -f "uvicorn.*src.api.main" 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
    print_warning "Killing stale uvicorn processes: ${OLD_PIDS//$'\n'/ }"
    echo "$OLD_PIDS" | xargs kill -15 2>/dev/null || true
    sleep 2
    STILL_ALIVE=$(pgrep -f "uvicorn.*src.api.main" 2>/dev/null || true)
    if [ -n "$STILL_ALIVE" ]; then
        print_warning "Force-killing: ${STILL_ALIVE//$'\n'/ }"
        echo "$STILL_ALIVE" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
fi

# Kill anything still holding the target port (belt-and-suspenders)
PORT_PIDS=$(lsof -ti:"$API_PORT" 2>/dev/null || true)
if [ -n "$PORT_PIDS" ]; then
    print_warning "Port $API_PORT still in use by PID(s): ${PORT_PIDS//$'\n'/ } — killing..."
    echo "$PORT_PIDS" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

WAIT=0
while lsof -ti:"$API_PORT" &>/dev/null; do
    if [ "$WAIT" -ge 10 ]; then
        print_error "Port $API_PORT is still busy after 10 s. Aborting."
        exit 1
    fi
    print_status "Waiting for port $API_PORT to free… (${WAIT}s)"
    sleep 1
    WAIT=$((WAIT + 1))
done
print_success "Port $API_PORT is free."

# ── Virtual environment ───────────────────────────────────────────────────────
print_step "Checking Python Environment..."
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found."
    print_status "Creating one now..."
    python3 -m venv .venv
fi
print_status "Activating virtual environment..."
source .venv/bin/activate

# ── Pre-flight checks ─────────────────────────────────────────────────────────
MISSING=0
[ ! -f "backend/data/bm25_index.pkl"  ] && print_error "BM25 index missing — run ingestion script." && MISSING=1
[ ! -d "backend/data/faiss_storage"   ] && print_error "FAISS index missing — run ingestion script." && MISSING=1
[ "$MISSING" -eq 1 ] && exit 1

# ── Frontend Build ────────────────────────────────────────────────────────────
print_step "Checking React Frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    npm install
fi

if [ ! -d "dist" ]; then
    print_status "Building React frontend for production..."
    npm run build
else
    print_status "Frontend build found. (If you made changes, run 'npm run build' inside frontend/)"
fi
cd ..

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
print_success "All checks passed. Launching server..."
print_status  "URL: http://$API_HOST:$API_PORT"
echo ""

# Note: The api is now located at backend.src.api.main due to the folder restructuring
export PYTHONPATH="$PROJECT_DIR/backend:$PYTHONPATH"

exec uvicorn src.api.main:app \
    --app-dir "$PROJECT_DIR/backend" \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --log-level "$LOG_LEVEL_LOWER"
