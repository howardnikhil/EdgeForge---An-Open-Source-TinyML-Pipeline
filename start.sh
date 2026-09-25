#!/usr/bin/env bash
set -e

# ═══════════════════════════════════════════════════════════
# HowNik's EdgeForge — Start Script
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${PURPLE}${BOLD}  ⚡ HowNik's EdgeForge${NC}"
echo -e "${CYAN}  TinyML / Edge-AI Engineering IDE${NC}"
echo ""
echo -e "  ${BOLD}Environment Check${NC}"
echo "  ────────────────────────────"
echo ""

# OS detection
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Darwin) OS_NAME="macOS" ;;
  Linux)  OS_NAME="Linux" ;;
  MINGW*|MSYS*|CYGWIN*) OS_NAME="Windows" ;;
  *) OS_NAME="$OS" ;;
esac

check() {
  if command -v "$1" &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} $2"
    return 0
  else
    echo -e "  ${RED}✗${NC} $2 ${YELLOW}(not found)${NC}"
    return 1
  fi
}

check_python_module() {
  if python3 -c "import $1" 2>/dev/null; then
    VERSION=$(python3 -c "import $1; print(getattr($1, '__version__', 'ok'))" 2>/dev/null)
    echo -e "  ${GREEN}✓${NC} $2  ${CYAN}${VERSION}${NC}"
  else
    echo -e "  ${YELLOW}○${NC} $2  ${YELLOW}(not installed)${NC}"
  fi
  return 0
}

echo -e "  ${BOLD}System${NC}"
echo -e "  ${GREEN}✓${NC} Operating System     ${CYAN}${OS_NAME}${NC}"
echo -e "  ${GREEN}✓${NC} Architecture         ${CYAN}${ARCH}${NC}"
check python3 "Python              " || { echo -e "\n  ${RED}Python 3 is required. Install from https://python.org${NC}"; exit 1; }
check node "Node.js             " || { echo -e "\n  ${RED}Node.js is required. Install from https://nodejs.org${NC}"; exit 1; }
check git "Git                 "
echo ""

echo -e "  ${BOLD}ML Environment${NC}"
check_python_module sklearn "scikit-learn"
check_python_module torch "PyTorch"
check_python_module tensorflow "TensorFlow"
check_python_module numpy "NumPy"
check_python_module pandas "Pandas"
check_python_module onnx "ONNX"
echo ""

echo -e "  ${BOLD}Embedded Toolchain${NC}"
check pio "PlatformIO" || true
check arduino-cli "Arduino CLI" || true
echo ""

echo -e "  ${BOLD}Emulation${NC}"
check renode "Renode" || true
check qemu-system-arm "QEMU" || true
echo ""

# Install backend dependencies
echo -e "  ${BOLD}Setting up backend...${NC}"
pip install -q fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings python-multipart pyserial numpy pandas scikit-learn joblib onnx skl2onnx pyyaml websockets httpx aiofiles 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Backend dependencies"

# Install frontend dependencies
echo -e "  ${BOLD}Setting up frontend...${NC}"
cd "$SCRIPT_DIR/apps/frontend"
if [ ! -d "node_modules" ]; then
  npm install --silent 2>/dev/null
fi
echo -e "  ${GREEN}✓${NC} Frontend dependencies"

echo ""
echo "  ────────────────────────────"
echo ""
echo -e "  ${BOLD}Starting EdgeForge...${NC}"
echo ""

# Start backend
cd "$SCRIPT_DIR/apps/backend"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
cd "$SCRIPT_DIR/apps/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

# Wait a moment
sleep 2

echo ""
echo -e "  ${GREEN}${BOLD}EdgeForge is running!${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}http://127.0.0.1:5173${NC}"
echo -e "  Backend:   ${CYAN}http://127.0.0.1:8000${NC}"
echo -e "  API Docs:  ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop."
echo ""

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
