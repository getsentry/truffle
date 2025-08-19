#!/bin/bash

# Truffle Slack Expert Search Service - FastAPI Server

# Exit on first error
set -euo pipefail

echo "Starting Truffle Slack Expert Search Service..."

# Install uv if it's not installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Install dependencies if needed
if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
    echo "Installing/updating dependencies..."
    uv sync
fi

# Start FastAPI server
echo "Starting FastAPI server on http://localhost:8002"

uv run python main.py
