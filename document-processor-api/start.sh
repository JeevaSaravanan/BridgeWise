#!/bin/bash

# Document Processing API Startup Script
# This script starts the Flask API for advanced document processing

echo "🚀 Starting Document Processing API..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed or not in PATH${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📁 Working directory: $SCRIPT_DIR${NC}"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}🐍 Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  No virtual environment found, using system Python${NC}"
fi

# Check if requirements.txt exists and install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📦 Checking dependencies...${NC}"
    
    # Check if key packages are installed
    python -c "import flask, flask_cors, PyPDF2, pdfplumber, fitz, docx, pptx" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}📥 Installing missing dependencies...${NC}"
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Failed to install dependencies${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ All dependencies are installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing essential packages...${NC}"
    pip install Flask Flask-CORS PyPDF2 pdfplumber PyMuPDF python-docx python-pptx
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found in current directory${NC}"
    exit 1
fi

# Check if port 5001 is available
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  Port 5001 is already in use${NC}"
    echo "Would you like to:"
    echo "1) Kill the process using port 5001"
    echo "2) Use a different port"
    echo "3) Exit"
    read -p "Enter your choice (1/2/3): " choice
    
    case $choice in
        1)
            echo -e "${YELLOW}🔄 Killing process on port 5001...${NC}"
            lsof -ti:5001 | xargs kill -9
            sleep 2
            ;;
        2)
            read -p "Enter port number: " port
            export FLASK_PORT=$port
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

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Default port
PORT=${FLASK_PORT:-5001}

echo ""
echo -e "${GREEN}🎯 Configuration:${NC}"
echo -e "   ${BLUE}App:${NC} $FLASK_APP"
echo -e "   ${BLUE}Port:${NC} $PORT"
echo -e "   ${BLUE}Debug:${NC} $FLASK_DEBUG"
echo -e "   ${BLUE}Max File Size:${NC} 16MB"
echo -e "   ${BLUE}Supported Formats:${NC} PDF, DOCX, PPTX"
echo ""

# Start the Flask app
echo -e "${GREEN}🚀 Starting Flask API server...${NC}"
echo -e "${BLUE}📍 API will be available at: http://localhost:$PORT${NC}"
echo -e "${BLUE}📍 Health check: http://localhost:$PORT/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo "========================================"

# Start with proper error handling
if [ "$PORT" != "5001" ]; then
    python -c "
import sys
sys.path.insert(0, '.')
from app import app
app.run(debug=True, host='0.0.0.0', port=$PORT)
"
else
    python app.py
fi

# Cleanup on exit
echo ""
echo -e "${BLUE}👋 Document Processing API stopped${NC}"
