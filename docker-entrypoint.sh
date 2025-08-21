#!/bin/sh
set -e

# Truffle Multi-Service Docker Entrypoint
# Launches the specified service based on SERVICE_NAME environment variable
#
# Port Selection Priority:
# 1. PORT (Railway's dynamic port)
# 2. Service-specific port (SLACK_BOT_PORT, INGESTOR_PORT, EXPERT_API_PORT)
# 3. Default fallback: 8000

SERVICE_NAME=${SERVICE_NAME:-slack_bot}

echo "Starting Truffle service: $SERVICE_NAME"

case "$SERVICE_NAME" in
  "slack_bot")
    echo "Launching Slack Bot service..."
    cd /app/slack_bot
    # Port fallback: PORT -> SLACK_BOT_PORT -> 8000
    export SLACK_BOT_PORT=${PORT:-${SLACK_BOT_PORT:-8000}}
    echo "Using port: $SLACK_BOT_PORT"
    exec python main.py
    ;;

  "ingestor")
    echo "Launching Ingestor service..."
    cd /app/ingestor
    # Port fallback: PORT -> INGESTOR_PORT -> 8000
    export INGESTOR_PORT=${PORT:-${INGESTOR_PORT:-8000}}
    echo "Using port: $INGESTOR_PORT"
    exec python main.py
    ;;

  "expert_api")
    echo "Launching Expert API service..."
    cd /app/expert_api
    # Port fallback: PORT -> EXPERT_API_PORT -> 8000
    export EXPERT_API_PORT=${PORT:-${EXPERT_API_PORT:-8000}}
    echo "Using port: $EXPERT_API_PORT"
    exec python main.py
    ;;

  *)
    echo "Error: Invalid SERVICE_NAME '$SERVICE_NAME'"
    echo "Valid options are: slack_bot, ingestor, expert_api"
    exit 1
    ;;
esac
