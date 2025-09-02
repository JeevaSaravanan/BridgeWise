#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting BridgeWise Full Stack Development Environment...${NC}"

# Function to kill background processes on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Backend stopped${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Frontend stopped${NC}"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "github-analyzer-api" ]; then
    echo -e "${RED}❌ Please run this script from the BridgeWise project root directory${NC}"
    exit 1
fi

# Start backend
echo -e "${BLUE}🔧 Starting FastAPI backend...${NC}"
cd github-analyzer-api
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${YELLOW}⚠️  Backend might not be ready yet. Continuing...${NC}"
fi

# Start frontend
echo -e "${BLUE}🎨 Starting Vite frontend...${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}🎉 Development environment started!${NC}"
echo ""
echo -e "${BLUE}📡 Services:${NC}"
echo -e "  Backend:  ${GREEN}http://localhost:8000${NC} (API docs: http://localhost:8000/docs)"
echo -e "  Frontend: ${GREEN}http://localhost:5173${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "  - The frontend will auto-reload on file changes"
echo "  - The backend supports hot-reload with uvicorn --reload"
echo "  - Check backend logs if API calls fail"
echo "  - Portfolio data is stored in PostgreSQL with localStorage fallback"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Wait for either process to exit
wait
