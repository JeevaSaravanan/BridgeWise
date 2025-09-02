#!/bin/bash

echo "🚀 Starting GitHub Repository Analyzer API..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the github-analyzer-api directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Start the API server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📚 API Documentation available at http://localhost:8000/docs"
echo "❤️  Health check available at http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"

# Start with uvicorn for better control
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
