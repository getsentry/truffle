# Multi-service Docker image for Truffle services (Phase 1 Optimized)
# Supports: slack_bot, ingestor, expert_api
# Usage: Set SERVICE_NAME environment variable to choose which service to run

# Stage 1: Build dependencies with build tools
FROM python:3.13-alpine AS builder

# Install build dependencies (only in builder stage)
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    postgresql-dev

# Install uv for faster Python package management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy all pyproject.toml files first for better layer caching
COPY slack_bot/pyproject.toml ./slack_bot/
COPY ingestor/pyproject.toml ./ingestor/
COPY expert_api/pyproject.toml ./expert_api/

# Install dependencies from all services using uv
# Install production dependencies only (exclude dev-dependencies from [tool.uv])
RUN cd slack_bot && uv pip install --system --no-cache-dir -e . && \
    cd ../ingestor && uv pip install --system --no-cache-dir -e . && \
    cd ../expert_api && uv pip install --system --no-cache-dir -e .

# Stage 2: Runtime image (lightweight, no build tools)
FROM python:3.13-alpine AS runtime

# Install only runtime dependencies
RUN apk add --no-cache \
    libpq \
    ca-certificates && \
    rm -rf /var/cache/apk/*

# Create non-root user for security
RUN adduser -D -u 1001 -h /app truffle

# Set working directory and ownership
WORKDIR /app
RUN chown truffle:truffle /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy all service source code
COPY --chown=truffle:truffle slack_bot/ ./slack_bot/
COPY --chown=truffle:truffle ingestor/ ./ingestor/
COPY --chown=truffle:truffle expert_api/ ./expert_api/

# Copy startup script
COPY --chown=truffle:truffle docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Switch to non-root user
USER truffle

# Set optimal environment variables
ENV SERVICE_NAME=slack_bot
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check without curl (using Python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Expose port 8000 (services can be configured to use different ports via env vars)
EXPOSE 8000

# Use the startup script as entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
