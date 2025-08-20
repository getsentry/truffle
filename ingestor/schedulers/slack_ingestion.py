import asyncio
import logging
from datetime import UTC, datetime

from services.queue_service import get_queue_service
from services.score_aggregation_service import get_aggregation_service
from services.slack_service import SlackService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Configuration constants
FIRST_RUN_HOURS = 24 * 30  # 30 days for initial historical import
PERIODIC_RUN_HOURS = 1  # 1 hour for regular periodic runs


async def run_slack_ingestion():
    """Main ingestion task - runs periodically"""
    logger.info("Starting Slack ingestion run")
    start_time = datetime.now(UTC)

    try:
        slack_service = SlackService()
        storage = StorageService()
        queue_service = get_queue_service()

        # Check if this is first run (empty database)
        is_first_run = await storage.is_database_empty()
        since_hours = FIRST_RUN_HOURS if is_first_run else PERIODIC_RUN_HOURS

        logger.info(
            f"{'First run' if is_first_run else 'Periodic run'} - "
            f"fetching messages from last {since_hours} hours"
        )

        # Get channels and users
        logger.info("Fetching channels and users from Slack...")
        channels = await slack_service.get_public_channels()
        users = await slack_service.get_workspace_users()

        logger.info(f"Found {len(channels)} channels and {len(users)} users")

        # Store/update users in database
        await storage.upsert_users(users)
        logger.info("Updated users in database")

        messages_enqueued = 0

        # Enqueue messages from each channel for background processing
        for channel in channels:
            logger.info(f"Enqueuing messages from channel: {channel['name']}")

            try:
                # Get messages since last run (or longer window for first run)
                async for message in slack_service.get_recent_messages(
                    channel["id"],
                    since_hours=since_hours,
                ):
                    # Replace user mentions for better text processing
                    if message.get("text"):
                        message["text"] = slack_service.replace_user_mentions(
                            message["text"], users
                        )

                    # Enqueue message for background processing
                    await queue_service.enqueue_message(message, channel, users)
                    messages_enqueued += 1

                    # Small batch processing - enqueue in batches to avoid overwhelming
                    if messages_enqueued % 100 == 0:
                        logger.info(f"Enqueued {messages_enqueued} messages so far...")
                        await asyncio.sleep(0.1)  # Brief pause between batches

            except Exception as e:
                logger.error(
                    f"Error enqueuing messages from channel {channel['name']}: {e}"
                )
                continue  # Continue with next channel

        duration = (datetime.now(UTC) - start_time).total_seconds()
        queue_stats = await queue_service.get_queue_stats()
        logger.info(
            f"Ingestion completed: {messages_enqueued} messages enqueued in {duration:.2f}s. "
            f"Queue stats: {queue_stats}"
        )

        # After first run, wait for workers to finish processing and aggregate scores
        if is_first_run and messages_enqueued > 0:
            logger.info(
                "First run detected - will aggregate scores after processing completes"
            )
            await _wait_for_processing_and_aggregate(queue_service)

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise


async def _wait_for_processing_and_aggregate(queue_service):
    """Wait for message processing to complete, then aggregate scores"""
    logger.info("Waiting for message processing to complete...")

    # Wait for queue to be empty (all messages processed)
    max_wait_minutes = 60  # Don't wait forever
    wait_cycles = 0
    max_cycles = max_wait_minutes * 6  # Check every 10 seconds

    while wait_cycles < max_cycles:
        stats = await queue_service.get_queue_stats()
        pending = stats.get("pending", 0)
        processing = stats.get("processing", 0)

        if pending == 0 and processing == 0:
            logger.info("All messages processed! Starting score aggregation...")
            break

        if wait_cycles % 30 == 0:  # Log every 5 minutes
            logger.info(
                f"Still processing: {pending} pending, {processing} processing..."
            )

        await asyncio.sleep(10)  # Wait 10 seconds
        wait_cycles += 1

    if wait_cycles >= max_cycles:
        logger.warning(
            "Timeout waiting for processing to complete, aggregating anyway..."
        )

    # Trigger score aggregation
    try:
        aggregation_service = get_aggregation_service()
        result = await aggregation_service.aggregate_all_scores()
        logger.info(f"Score aggregation completed: {result}")
    except Exception as e:
        logger.error(f"Score aggregation failed: {e}", exc_info=True)
