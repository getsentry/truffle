#!/bin/bash

# Truffle Slack Ingestion Service - FastAPI Server
# Run this to start the service with periodic Slack ingestion

# Exit on first error
set -euo pipefail

echo "Starting Truffle Slack Ingestion Service..."

# Install uv if it's not installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Check environment variables
if [ -z "$SLACK_BOT_AUTH_TOKEN" ]; then
    echo "Error: SLACK_BOT_AUTH_TOKEN environment variable is required"
    exit 1
fi

if [ "$CLASSIFY_EXPERTISE" = "1" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is required when CLASSIFY_EXPERTISE=1"
    exit 1
fi

# Install dependencies if needed
if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
    echo "Installing/updating dependencies..."
    uv sync
fi

# Start FastAPI server
echo "Starting FastAPI server on http://localhost:8001"
echo "API endpoints:"
echo "  - GET  /           - Service status"
echo "  - GET  /health     - Health check"
echo "  - POST /trigger-ingestion - Manual trigger"
echo "  - GET  /jobs       - List scheduled jobs"
echo ""
echo "Automatic ingestion runs every 15 minutes"
echo "Press Ctrl+C to stop"
echo ""

uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
