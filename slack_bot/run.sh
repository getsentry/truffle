#!/bin/bash

# Truffle Slack Bot Service
# Run this to start the Slack bot service

# Exit on first error
set -euo pipefail

echo "Starting Truffle Slack Bot Service..."

# Install uv if it's not installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Check required environment variables
if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
    echo "Warning: SLACK_BOT_TOKEN environment variable not set"
fi

if [ -z "${SLACK_SIGNING_SECRET:-}" ]; then
    echo "Warning: SLACK_SIGNING_SECRET environment variable not set"
fi

# Install dependencies if needed
if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
    echo "Installing/updating dependencies..."
    uv sync
fi

# Start FastAPI server
echo "Starting Slack Bot service on http://localhost:8003"
echo "API endpoints:"
echo "  - GET  /           - Service status"
echo "  - GET  /health     - Health check"
echo "  - POST /slack/events - Slack event handler"
echo "  - GET  /docs       - API documentation"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uv run uvicorn main:app --host ${SLACK_BOT_HOST:-0.0.0.0} --port ${SLACK_BOT_PORT:-8003} --reload
