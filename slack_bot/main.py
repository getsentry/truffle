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
from services import EventProcessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize event processor
# TODO: Get bot_user_id from Slack API or config
event_processor = EventProcessor(bot_user_id=None)

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
    if payload.type == "event_callback":
        try:
            # Process the event and extract expert query
            expert_query = await event_processor.process_slack_event(
                payload.model_dump()
            )

            if expert_query:
                logger.info(
                    f"Extracted expert query: {expert_query.query_type} "
                    f"for skills: {expert_query.skills}"
                )

                # TODO Phase 3: Call expert_api service with the query
                # TODO Phase 4: Format response for Slack
                # TODO Phase 5: Send response back to Slack

                return SlackEventsResponse(
                    ok=True,
                    message=f"Found expert query for: {', '.join(expert_query.skills)}",
                )
            else:
                logger.info("No expert query extracted from event")
                return SlackEventsResponse(
                    ok=True, message="Event processed, no action needed"
                )

        except Exception as e:
            logger.error(f"Error processing Slack event: {e}", exc_info=True)
            return SlackEventsResponse(ok=False, message="Error processing event")

    return SlackEventsResponse(ok=True, message="Event processed")


@app.post("/ask", response_model=AskResponse)
async def ask(_: AskRequest) -> AskResponse:
    """Manual ask endpoint for testing"""
    return AskResponse(ok=True, answer="example response")


@app.get("/debug/stats")
async def debug_stats():
    """Debug endpoint to show processing statistics"""
    stats = event_processor.get_processing_stats()
    return {
        "service": "Truffle Slack Bot",
        "processing_stats": stats,
        "supported_skills_sample": event_processor.query_parser.get_supported_skills()[
            :20
        ],
    }


@app.post("/debug/parse")
async def debug_parse_query(request: dict):
    """Debug endpoint to test query parsing"""
    text = request.get("text", "")
    if not text:
        return {"error": "No text provided"}

    # Create a mock parsed message for testing
    from models.slack_models import ParsedSlackMessage

    mock_message = ParsedSlackMessage(
        text=text,
        cleaned_text=text,  # In real usage this would be cleaned
        user_id="U123TEST",
        channel_id="C123TEST",
        timestamp="123456789",
        is_question=True,
        is_app_mention=True,
    )

    # Parse the query
    expert_query = event_processor.query_parser.parse_query(mock_message)

    if expert_query:
        return {
            "input": text,
            "extracted_query": {
                "skills": expert_query.skills,
                "query_type": expert_query.query_type,
                "confidence": expert_query.confidence,
            },
        }
    else:
        return {"input": text, "result": "No expert query found"}


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
