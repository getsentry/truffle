"""Slack Bot Service - Expert search integration for Slack"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

import sentry_sdk
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from slack_sdk.web.async_client import AsyncWebClient

from config import settings
from models import HealthResponse, SlackEventsRequest, SlackEventsResponse
from services import EventProcessor, ExpertAPIClient, SkillCacheService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services (will be set in lifespan)
expert_api_client: ExpertAPIClient | None = None
skill_cache_service: SkillCacheService | None = None
event_processor: EventProcessor | None = None
slack_client: AsyncWebClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown tasks"""
    global expert_api_client, skill_cache_service, event_processor, slack_client

    # Initialize Sentry
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            debug=True,
        )

    logger.info("Starting up Slack Bot service...")

    slack_client = AsyncWebClient(token=settings.slack_bot_auth_token)
    expert_api_client = ExpertAPIClient(base_url=settings.expert_api_url)

    # Check Expert API availability
    try:
        if await expert_api_client.is_available():
            logger.info("Expert API is available")
        else:
            logger.warning("Expert API is not responding")
    except Exception as e:
        logger.error(f"Failed to check Expert API: {e}")

    # Pre-populate skill cache
    skill_cache_service = SkillCacheService(expert_api_client, cache_ttl_minutes=60)
    try:
        await skill_cache_service.refresh_cache()
        logger.info("Skill cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize skill cache: {e}")

    # Initialize Event Processor with skill cache
    event_processor = EventProcessor(skill_cache_service, bot_user_id=None)

    logger.info("All services initialized successfully")

    yield

    logger.info("Shutting down Slack Bot service...")


# Create FastAPI app
app = FastAPI(
    title="Truffle Slack Bot",
    description="Slack bot for expert search and team knowledge discovery",
    version="1.0.0",
    lifespan=lifespan,
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
        if not event_processor:
            return SlackEventsResponse(ok=False, message="Service not initialized")

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

                if not expert_api_client:
                    return SlackEventsResponse(
                        ok=False, message="Expert API client not initialized"
                    )

                try:
                    # Call Expert API to find experts
                    search_response = await expert_api_client.search_experts(
                        skills=expert_query.skills,
                        limit=5,  # Limit results for Slack
                        min_confidence=0.7,  # Only high-confidence matches
                    )

                    if search_response.results:
                        response_message = format_expert_response(
                            expert_query.skills, search_response.results
                        )

                        # Send reply to Slack channel
                        await send_slack_reply(payload.model_dump(), response_message)

                        return SlackEventsResponse(ok=True, message=response_message)
                    else:
                        skills_text = ", ".join(expert_query.skills)
                        no_experts_message = f"No experts found for {skills_text}"

                        # Send reply to Slack channel
                        await send_slack_reply(payload.model_dump(), no_experts_message)

                        return SlackEventsResponse(
                            ok=True,
                            message=no_experts_message,
                        )

                except Exception as api_error:
                    logger.error(f"Expert API call failed: {api_error}")
                    error_message = (
                        "Sorry, I couldn't search for experts right now. "
                        "Please try again later."
                    )

                    # Send error reply to Slack channel
                    await send_slack_reply(payload.model_dump(), error_message)

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


@app.get("/debug/stats")
async def debug_stats():
    """Debug endpoint to show processing statistics"""
    if not event_processor:
        return {"error": "Event processor not initialized"}

    stats = await event_processor.get_processing_stats()

    # Check Expert API status
    expert_api_status = "unknown"
    if expert_api_client:
        try:
            expert_api_status = (
                "available" if await expert_api_client.is_available() else "unavailable"
            )
        except Exception:
            expert_api_status = "error"

    # Get skill cache stats
    cache_stats = {}
    if skill_cache_service:
        cache_stats = skill_cache_service.get_cache_stats()

    return {
        "service": "Truffle Slack Bot",
        "processing_stats": stats,
        "expert_api_status": expert_api_status,
        "expert_api_url": settings.expert_api_url,
        "skill_cache_stats": cache_stats,
    }


async def send_slack_reply(event_data: dict, message: str) -> None:
    """Send a reply message to the Slack channel"""
    if not slack_client:
        logger.error("Slack client not initialized")
        return

    try:
        # Extract event details
        event = event_data.get("event", {})
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get(
            "ts"
        )  # Reply in thread if possible

        if not channel_id:
            logger.error("No channel ID found in event data")
            return

        # Send the message
        response = await slack_client.chat_postMessage(
            channel=channel_id,
            text=message,
            thread_ts=thread_ts,  # This makes it a threaded reply
        )

        if response["ok"]:
            logger.info(f"Successfully sent reply to channel {channel_id}")
        else:
            logger.error(f"Failed to send Slack message: {response.get('error')}")

    except Exception as e:
        logger.error(f"Error sending Slack reply: {e}", exc_info=True)


def format_expert_response(skills: list[str], experts: list) -> str:
    """Format expert search results into a user-friendly message"""
    skills_text = ", ".join(skills)

    if len(experts) == 1:
        expert = experts[0]
        mention = format_expert_mention(expert)
        confidence = expert.confidence_score
        evidence = expert.evidence_count

        return (
            f"✨ Found 1 expert for *{skills_text}*: ✨\n"
            f"• {mention} (confidence: {confidence:.1%}, "
            f"{evidence} evidence{'s' if evidence != 1 else ''})"
        )

    elif len(experts) <= 5:
        expert_lines = []
        for expert in experts:
            mention = format_expert_mention(expert)
            confidence = expert.confidence_score
            evidence = expert.evidence_count
            expert_lines.append(
                f"• {mention} (confidence: {confidence:.1%}, "
                f"{evidence} evidence{'s' if evidence != 1 else ''})"
            )

        return f"✨ Found {len(experts)} experts for *{skills_text}*: ✨\n" + "\n".join(
            expert_lines
        )

    else:
        # Show top 3 + summary for large lists
        top_experts = []
        for expert in experts[:3]:
            mention = format_expert_mention(expert)
            confidence = expert.confidence_score
            top_experts.append(f"• {mention} ({confidence:.1%})")

        remaining = len(experts) - 3
        return (
            f"✨ Found {len(experts)} experts for *{skills_text}*: ✨\n"
            + "\n".join(top_experts)
            + f"\n... and {remaining} more expert{'s' if remaining != 1 else ''}"
        )


def format_expert_mention(expert) -> str:
    """Format an expert as a clickable Slack mention"""
    user_id = expert.user_id

    return f"<@{user_id}>"


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting Truffle Slack Bot on "
        f"{settings.slack_bot_host}:{settings.slack_bot_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.slack_bot_host,
        port=settings.slack_bot_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
