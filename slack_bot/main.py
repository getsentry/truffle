"""Slack Bot Service - Expert search integration for Slack"""

import logging
from contextlib import asynccontextmanager
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
from services import EventProcessor, ExpertAPIClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
# TODO: Get bot_user_id from Slack API or config
event_processor = EventProcessor(bot_user_id=None)
expert_api_client = ExpertAPIClient(base_url=settings.expert_api_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown tasks"""

    # Startup: Initialize services and check API availability
    logger.info("Starting up Slack Bot service...")

    # Check Expert API availability
    try:
        if await expert_api_client.is_available():
            logger.info("✅ Expert API is available")
        else:
            logger.warning("⚠️ Expert API is not responding")
    except Exception as e:
        logger.error(f"❌ Failed to check Expert API: {e}")

    yield

    # Shutdown: Cleanup resources
    logger.info("Shutting down Slack Bot service...")
    await expert_api_client.close()


# Create FastAPI app
app = FastAPI(
    title="Truffle Slack Bot",
    description="Slack bot for expert search and team knowledge discovery",
    version="1.0.0",
    lifespan=lifespan,
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

                try:
                    # Call Expert API to find experts
                    search_response = await expert_api_client.search_experts(
                        skills=expert_query.skills,
                        limit=5,  # Limit results for Slack
                        min_confidence=0.7,  # Only high-confidence matches
                    )

                    if search_response.results:
                        expert_names = [
                            result.display_name or result.user_name or result.user_id
                            for result in search_response.results
                        ]

                        response_message = (
                            f"Found {len(search_response.results)} experts for "
                            f"{', '.join(expert_query.skills)}: "
                            f"{', '.join(expert_names[:3])}"
                        )

                        if len(expert_names) > 3:
                            response_message += f" and {len(expert_names) - 3} more"

                        # TODO Phase 4: Enhanced formatting and Slack message sending

                        return SlackEventsResponse(ok=True, message=response_message)
                    else:
                        skills_text = ", ".join(expert_query.skills)
                        return SlackEventsResponse(
                            ok=True,
                            message=f"No experts found for {skills_text}",
                        )

                except Exception as api_error:
                    logger.error(f"Expert API call failed: {api_error}")
                    error_message = (
                        "Sorry, I couldn't search for experts right now. "
                        "Please try again later."
                    )
                    return SlackEventsResponse(ok=True, message=error_message)
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

    # Check Expert API status
    expert_api_status = "unknown"
    try:
        expert_api_status = (
            "available" if await expert_api_client.is_available() else "unavailable"
        )
    except Exception:
        expert_api_status = "error"

    return {
        "service": "Truffle Slack Bot",
        "processing_stats": stats,
        "expert_api_status": expert_api_status,
        "expert_api_url": settings.expert_api_url,
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


@app.post("/debug/expert-search")
async def debug_expert_search(request: dict):
    """Debug endpoint to test Expert API search"""
    skills = request.get("skills", [])
    if not skills:
        return {"error": "No skills provided"}

    try:
        search_response = await expert_api_client.search_experts(
            skills=skills, limit=10, min_confidence=0.0
        )

        return {
            "query": {"skills": skills},
            "results": [
                {
                    "user_id": result.user_id,
                    "display_name": result.display_name,
                    "skills": result.skills,
                    "confidence": result.confidence_score,
                    "evidence_count": result.evidence_count,
                }
                for result in search_response.results
            ],
            "total_found": search_response.total_found,
            "processing_time_ms": search_response.processing_time_ms,
        }

    except Exception as e:
        return {
            "error": f"Expert API search failed: {str(e)}",
            "query": {"skills": skills},
        }


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
