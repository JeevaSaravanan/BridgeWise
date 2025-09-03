#!/bin/bash
# Activation script for document-processor-api virtual environment

echo "🔧 Activating document-processor-api virtual environment..."
cd "$(dirname "$0")"
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
pip list --format=columns

echo ""
echo "🚀 To start the Flask API server, run:"
echo "   export AZURE_OPENAI_KEY=\$AZURE_OPENAI_KEY"
echo "   python app.py"
echo ""
echo "📋 Available endpoints:"
echo "   • GET  /health - Health check"
echo "   • POST /process-document - Full document processing with GenAI"
echo "   • POST /extract-text - Text extraction only"
