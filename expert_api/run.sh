#!/bin/bash

# Truffle Expert Search API Service
# Run this to start the expert search service

# Exit on first error
set -euo pipefail

echo "Starting Truffle Expert Search API Service..."

# Install uv if it's not installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Check database connection
if [ -z "${TRUFFLE_DB_URL:-}" ]; then
    echo "Warning: TRUFFLE_DB_URL environment variable not set, using default"
fi

# Install dependencies if needed
if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
    echo "Installing/updating dependencies..."
    uv sync
fi

# Start FastAPI server
echo "Starting Expert Search API server on ${EXPERT_API_HOST:-0.0.0.0}:${EXPERT_API_PORT:-8002}"
echo "API endpoints:"
echo "  - GET  /           - Service status"
echo "  - GET  /health     - Health check"
echo "  - GET  /docs       - API documentation"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uv run uvicorn main:app --host ${EXPERT_API_HOST:-0.0.0.0} --port ${EXPERT_API_PORT:-8002} --reload
