#!/usr/bin/env bash
set -Eeuo pipefail

# Document Processing API Startup Script (FastAPI)
# Starts the FastAPI service via uvicorn

echo "🚀 Starting Document Processing API (FastAPI)..."
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helpers -----------------------------------------------------------------
port_in_use () {
  local p="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -Pi ":$p" -sTCP:LISTEN -t >/dev/null
  elif command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :$p" | grep -q LISTEN
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn | awk '{print $4}' | grep -E "[:.]$p$" >/dev/null
  else
    return 1
  fi
}

need_cmd () {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo -e "${RED}❌ Required command not found: $1${NC}"
    exit 1
  fi
}

# --- Basic checks -------------------------------------------------------------
# Python
if ! command -v python >/dev/null 2>&1; then
    echo -e "${RED}❌ Python is not installed or not in PATH${NC}"
    exit 1
fi

# Working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo -e "${BLUE}📁 Working directory: $SCRIPT_DIR${NC}"

# Activate venv if present
if [ -d "venv" ]; then
    echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
    # shellcheck disable=SC1091
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  No virtual environment found, using system Python${NC}"
fi

# Dependencies  ✅ FIXED then/else/fi syntax here
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📦 Checking dependencies (requirements.txt)...${NC}"
    # Try a quick import probe for key libs
    if ! python - <<'PY' 2>/dev/null
import fastapi, uvicorn, PyPDF2, pdfplumber, fitz, docx, pptx, dotenv, openai
PY
    then
        echo -e "${YELLOW}📥 Installing missing dependencies...${NC}"
        python -m pip install -r requirements.txt
    else
        echo -e "${GREEN}✅ All key dependencies appear installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing essential packages...${NC}"
    python -m pip install fastapi uvicorn PyPDF2 pdfplumber PyMuPDF python-docx python-pptx python-dotenv openai
fi

# Ensure uvicorn is available
if ! command -v uvicorn >/dev/null 2>&1; then
  echo -e "${YELLOW}ℹ️  uvicorn not found on PATH, will try 'python -m uvicorn'${NC}"
  UVICORN_CMD=(python -m uvicorn)
else
  UVICORN_CMD=(uvicorn)
fi

# Load .env from project root (one level up)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${BLUE}🔐 Loading environment variables from $PROJECT_ROOT/.env${NC}"
    set -a
    # shellcheck disable=SC1090
    source "$PROJECT_ROOT/.env"
    set +a
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found at $PROJECT_ROOT/.env${NC}"
fi

# --- App module detection -----------------------------------------------------
APP_MODULE_DEFAULT="fastapi_document_processor:app"
if [ -f "fastapi_document_processor.py" ]; then
  APP_MODULE="${APP_MODULE:-$APP_MODULE_DEFAULT}"
elif [ -f "app.py" ]; then
  APP_MODULE="${APP_MODULE:-app:app}"
else
  echo -e "${RED}❌ Could not find fastapi_document_processor.py or app.py in current directory${NC}"
  echo -e "${YELLOW}   Set APP_MODULE manually, e.g.: APP_MODULE='path.to.module:app' ./start.sh${NC}"
  exit 1
fi

# --- Port handling ------------------------------------------------------------
PORT_DEFAULT=5001
PORT="${PORT:-${FASTAPI_PORT:-$PORT_DEFAULT}}"

if port_in_use "$PORT"; then
    echo -e "${YELLOW}⚠️  Port $PORT is already in use${NC}"
    echo "Would you like to:"
    echo "1) Kill the process using port $PORT"
    echo "2) Use a different port"
    echo "3) Exit"
    read -r -p "Enter your choice (1/2/3): " choice
    case "$choice" in
        1)
            echo -e "${YELLOW}🔄 Killing process on port $PORT...${NC}"
            if command -v lsof >/dev/null 2>&1; then
              lsof -ti:"$PORT" | xargs -r kill -9 || true
            elif command -v ss >/dev/null 2>&1; then
              echo -e "${YELLOW}Please kill the process manually; 'ss' doesn't provide PIDs directly here.${NC}"
            fi
            sleep 2
            ;;
        2)
            read -r -p "Enter port number: " PORT
            ;;
        3)
            echo -e "${BLUE}👋 Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
fi

HOST="${HOST:-0.0.0.0}"
RELOAD="${RELOAD:-1}"

echo ""
echo -e "${GREEN}🎯 Configuration:${NC}"
echo -e "   ${BLUE}Module:${NC} $APP_MODULE"
echo -e "   ${BLUE}Host:${NC} $HOST"
echo -e "   ${BLUE}Port:${NC} $PORT"
echo -e "   ${BLUE}Reload:${NC} $RELOAD"
echo -e "   ${BLUE}Max File Size:${NC} 16MB"
echo -e "   ${BLUE}Supported Formats:${NC} PDF, DOCX, PPTX"
echo ""

# --- Start server -------------------------------------------------------------
echo -e "${GREEN}🚀 Starting FastAPI server with uvicorn...${NC}"
echo -e "${BLUE}📍 API will be available at: http://localhost:$PORT${NC}"
echo -e "${BLUE}📍 Health check: http://localhost:$PORT/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo "========================================"

EXTRA_ARGS=()
if [ "$RELOAD" = "1" ]; then
  EXTRA_ARGS+=(--reload)
fi

# Run uvicorn
"${UVICORN_CMD[@]}" "$APP_MODULE" --host "$HOST" --port "$PORT" "${EXTRA_ARGS[@]}"

echo ""
echo -e "${BLUE}👋 Document Processing API stopped${NC}"
