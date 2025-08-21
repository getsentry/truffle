#!/bin/sh
set -e

# Truffle Multi-Service Docker Entrypoint
# Launches the specified service based on SERVICE_NAME environment variable

SERVICE_NAME=${SERVICE_NAME:-slack_bot}

echo "Starting Truffle service: $SERVICE_NAME"

case "$SERVICE_NAME" in
  "slack_bot")
    echo "Launching Slack Bot service..."
    cd /app/slack_bot
    export SLACK_BOT_PORT=${SLACK_BOT_PORT:-8000}
    exec python main.py
    ;;

  "ingestor")
    echo "Launching Ingestor service..."
    cd /app/ingestor
    export INGESTOR_PORT=${INGESTOR_PORT:-8000}
    exec python main.py
    ;;

  "expert_api")
    echo "Launching Expert API service..."
    cd /app/expert_api
    export EXPERT_API_PORT=${EXPERT_API_PORT:-8000}
    exec python main.py
    ;;

  *)
    echo "Error: Invalid SERVICE_NAME '$SERVICE_NAME'"
    echo "Valid options are: slack_bot, ingestor, expert_api"
    exit 1
    ;;
esac
