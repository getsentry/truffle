import asyncio
import logging
from datetime import UTC, datetime

from processors.message_processor import MessageProcessor
from services.slack_service import SlackService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


async def run_slack_ingestion():
    """Main ingestion task - runs periodically"""
    logger.info("Starting Slack ingestion run")
    start_time = datetime.now(UTC)

    try:
        slack_service = SlackService()
        processor = MessageProcessor()
        storage = StorageService()

        # Get channels and users
        logger.info("Fetching channels and users from Slack...")
        channels = await slack_service.get_public_channels()
        users = await slack_service.get_workspace_users()

        logger.info(f"Found {len(channels)} channels and {len(users)} users")

        # Store/update users in database
        await storage.upsert_users(users)
        logger.info("Updated users in database")

        messages_processed = 0

        # Process messages from each channel
        for channel in channels:
            logger.info(f"Processing channel: {channel['name']}")

            try:
                # Get messages since last run (or last 1 hour for periodic runs)
                async for message in slack_service.get_recent_messages(
                    channel["id"],
                    since_hours=1,  # Only new messages from last hour
                ):
                    # Replace user mentions for better text processing
                    if message.get("text"):
                        message["text"] = slack_service.replace_user_mentions(
                            message["text"], users
                        )

                    # Process message through pipeline
                    await processor.process_message(message, channel, users)
                    messages_processed += 1

                    # Add small delay to avoid overwhelming the classifier
                    if messages_processed % 10 == 0:
                        await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing channel {channel['name']}: {e}")
                continue  # Continue with next channel

        duration = (datetime.now(UTC) - start_time).total_seconds()
        logger.info(
            f"Ingestion completed: {messages_processed} messages in {duration:.2f}s"
        )

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise
