#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source environment if present
if [[ -f .env ]]; then
	export $(grep -v '^#' .env | xargs -I {} echo {}) 2>/dev/null || true
elif [[ -f .env.example ]]; then
	export $(grep -v '^#' .env.example | xargs -I {} echo {}) 2>/dev/null || true
fi

uvicorn app:app --host 0.0.0.0 --port 4000 --reload "$@"
