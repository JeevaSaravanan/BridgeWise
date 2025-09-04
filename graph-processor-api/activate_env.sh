#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Virtual environment created and activated."
fi

# Make sure all required packages are installed
pip install neo4j python-dotenv fastapi "uvicorn[standard]" pydantic langchain-openai pinecone python-dateutil requests
