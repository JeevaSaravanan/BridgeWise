#!/bin/bash

echo "🚀 Setting up BridgeWise Full Stack Application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "github-analyzer-api" ]; then
    echo -e "${RED}❌ Please run this script from the BridgeWise project root directory${NC}"
    exit 1
fi

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed.${NC}"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    echo "Please install Python 3 from https://python.org/"
    exit 1
fi

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️  PostgreSQL is not installed or not in PATH.${NC}"
    echo "Please ensure PostgreSQL is installed and running."
    echo "You can use Docker with: docker-compose up -d"
fi

echo -e "${GREEN}✅ Prerequisites check completed${NC}"

# Setup database
echo -e "${BLUE}🗄️  Setting up database...${NC}"
if [ -f "setup-postgres.sh" ]; then
    chmod +x setup-postgres.sh
    ./setup-postgres.sh
else
    echo -e "${YELLOW}⚠️  setup-postgres.sh not found. Please ensure PostgreSQL is configured.${NC}"
fi

# Install frontend dependencies
echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
npm install

# Install backend dependencies
echo -e "${BLUE}📦 Installing backend dependencies...${NC}"
cd github-analyzer-api
pip3 install -r requirements.txt
cd ..

echo -e "${GREEN}✅ Setup completed!${NC}"
echo ""
echo -e "${BLUE}🚀 To start the application:${NC}"
echo ""
echo -e "${YELLOW}Backend (FastAPI):${NC}"
echo "  cd github-analyzer-api && ./start.sh"
echo "  API will be available at: http://localhost:8000"
echo "  API docs at: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Frontend (Vite + React):${NC}"
echo "  npm run dev"
echo "  Frontend will be available at: http://localhost:5173"
echo ""
echo -e "${YELLOW}Database operations:${NC}"
echo "  npm run db:migrate  # Run migrations"
echo "  npm run db:seed     # Seed sample data"
echo "  npm run db:status   # Check database status"
echo ""
echo -e "${GREEN}🎉 Happy coding!${NC}"
