# Multi-service Docker image for Truffle services
# Supports: slack_bot, ingestor, expert_api
# Usage: Set SERVICE_NAME environment variable to choose which service to run

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install uv

# Copy all pyproject.toml files to install dependencies
COPY slack_bot/pyproject.toml ./slack_bot/
COPY ingestor/pyproject.toml ./ingestor/
COPY expert_api/pyproject.toml ./expert_api/

# Install dependencies from all services using uv
# Note: uv add requires a pyproject.toml in current dir, so we'll use uv pip install
RUN cd slack_bot && uv pip install --system -e . && \
    cd ../ingestor && uv pip install --system -e . && \
    cd ../expert_api && uv pip install --system -e .

# Copy all service source code
COPY slack_bot/ ./slack_bot/
COPY ingestor/ ./ingestor/
COPY expert_api/ ./expert_api/

# Copy startup script
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Set default environment variables
ENV SERVICE_NAME=slack_bot
ENV PYTHONPATH=/app

# Health check endpoint varies by service, so we'll check port 8000 generically
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port 8000 (services can be configured to use different ports via env vars)
EXPOSE 8000

# Use the startup script as entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
