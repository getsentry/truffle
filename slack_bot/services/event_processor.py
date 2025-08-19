"""Main event processing service that coordinates Slack event handling"""

import logging
from typing import Any

from models.slack_models import ExpertQuery
from services.query_parser import QueryParser
from services.slack_event_parser import SlackEventParser

logger = logging.getLogger(__name__)


class EventProcessor:
    """Coordinates Slack event processing and expert query extraction"""

    def __init__(self, bot_user_id: str | None = None):
        self.slack_parser = SlackEventParser(bot_user_id=bot_user_id)
        self.query_parser = QueryParser()

    async def process_slack_event(
        self, event_data: dict[str, Any]
    ) -> ExpertQuery | None:
        """Process a Slack event and return an expert query if found"""
        try:
            # Parse the event context
            context = self.slack_parser.parse_event(event_data)
            if not context:
                logger.warning("Failed to parse event context")
                return None

            # Only process events where the bot was mentioned or it's a DM
            if not context.bot_mentioned:
                logger.debug("Bot not mentioned, skipping event")
                return None

            # Extract the message from event_callback events
            if context.event_type == "event_callback" and "event" in event_data:
                nested_event = event_data["event"]
                nested_type = nested_event.get("type", "")

                if nested_type in ["app_mention", "message"]:
                    # Parse the message
                    parsed_message = self.slack_parser.parse_message(nested_event)
                    if not parsed_message:
                        logger.warning("Failed to parse message")
                        return None

                    # Check if we should process this message
                    if not self.slack_parser.should_process_message(parsed_message):
                        logger.info("Message doesn't require processing")
                        return None

                    # Extract expert query from the message
                    expert_query = self.query_parser.parse_query(parsed_message)
                    if expert_query:
                        logger.info(
                            f"Successfully extracted expert query: {expert_query.query_type} for {expert_query.skills}"
                        )
                        return expert_query
                    else:
                        logger.info("No expert query found in message")
                        return None

            logger.debug(
                f"Event type {context.event_type} not supported for processing"
            )
            return None

        except Exception as e:
            logger.error(f"Error processing Slack event: {e}", exc_info=True)
            return None

    def get_processing_stats(self) -> dict[str, Any]:
        """Get statistics about event processing"""
        return {
            "supported_skills_count": len(self.query_parser.get_supported_skills()),
            "query_patterns_count": len(self.query_parser.compiled_patterns),
            "bot_user_id": self.slack_parser.bot_user_id,
        }
