"""Slack Bot Service - Expert search integration for Slack"""

import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from config import settings
from models import (
    AskRequest,
    AskResponse,
    HealthResponse,
    SlackEventsRequest,
    SlackEventsResponse,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Truffle Slack Bot",
    description="Slack bot for expert search and team knowledge discovery",
    version="1.0.0",
)

# Add CORS middleware for cross-service communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.expert_api_url,
        settings.ingestor_url,
        "http://localhost:3000",  # For potential web UI
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - service status"""
    return {
        "service": "Truffle Slack Bot",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "description": "Slack bot for expert search and team knowledge discovery",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(status="ok")


@app.post("/slack/events", response_model=SlackEventsResponse)
async def slack_events(payload: SlackEventsRequest):
    """Handle Slack events (app_mention, message.im)"""
    logger.info(f"Received Slack event: {payload.type}")

    # Handle Slack URL verification challenge
    if payload.type == "url_verification" and payload.challenge:
        logger.info("Handling URL verification challenge")
        return PlainTextResponse(payload.challenge)

    # Handle actual events
    if payload.type == "event_callback" and payload.event:
        event = payload.event
        event_type = event.get("type")

        logger.info(f"Processing event type: {event_type}")

        if event_type in ["app_mention", "message"]:
            # Extract message details
            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")

            logger.info(f"Message from user {user} in channel {channel}: {text}")

            # TODO: Process the message and call expert_api
            # This will be implemented in Phase 2

    return SlackEventsResponse(ok=True, message="Event processed")


@app.post("/ask", response_model=AskResponse)
async def ask(_: AskRequest) -> AskResponse:
    """Manual ask endpoint for testing"""
    return AskResponse(ok=True, answer="example response")


if __name__ == "__main__":
    import uvicorn

    logger.info(
        f"Starting Slack Bot on {settings.slack_bot_host}:{settings.slack_bot_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.slack_bot_host,
        port=settings.slack_bot_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
