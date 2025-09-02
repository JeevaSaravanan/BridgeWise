#!/bin/bash

# Document Processing API Stop Script
# This script stops the Flask API server

echo "🛑 Stopping Document Processing API..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find and kill processes on port 5001
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}🔄 Stopping Flask API on port 5001...${NC}"
    lsof -ti:5001 | xargs kill -9
    sleep 2
    
    # Check if process was killed
    if ! lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ Document Processing API stopped successfully${NC}"
    else
        echo -e "${RED}❌ Failed to stop the API${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No Flask API running on port 5001${NC}"
fi

# Also check for any Python processes running app.py
PYTHON_PIDS=$(pgrep -f "python.*app.py")
if [ ! -z "$PYTHON_PIDS" ]; then
    echo -e "${YELLOW}🔄 Stopping Python app.py processes...${NC}"
    echo "$PYTHON_PIDS" | xargs kill -9
    echo -e "${GREEN}✅ Python processes stopped${NC}"
fi

echo -e "${GREEN}🏁 All Document Processing API processes stopped${NC}"
