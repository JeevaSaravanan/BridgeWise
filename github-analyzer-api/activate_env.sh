#!/bin/bash
# Activation script for github-analyzer-api virtual environment

echo "🔧 Activating github-analyzer-api virtual environment..."
cd "$(dirname "$0")"
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
pip list --format=columns

echo ""
echo "🚀 To start the FastAPI server, run:"
echo "   export AZURE_OPENAI_KEY=\$AZURE_OPENAI_KEY"
echo "   uvicorn main:app --reload --port 8000"
echo ""
echo "📋 Available endpoints:"
echo "   • GET  /docs - FastAPI documentation"
echo "   • POST /analyze - GitHub repository analysis with AI"
echo "   • Comprehensive portfolio management endpoints"
