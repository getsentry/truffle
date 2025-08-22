import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from config import settings
from database import create_tables
from database.operations import drop_tables
from schedulers.slack_ingestion import run_slack_ingestion
from scripts.import_taxonomy import import_taxonomy_files
from services.queue_service import get_queue_service
from services.score_aggregation_service import get_aggregation_service
from services.slack_service import SlackService
from services.storage_service import StorageService
from workers import get_worker_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure SQLAlchemy logging based on DEBUG_SQL setting
sql_log_level = logging.INFO if settings.debug_sql else logging.WARNING
logging.getLogger("sqlalchemy.engine").setLevel(sql_log_level)
logging.getLogger("sqlalchemy.dialects").setLevel(sql_log_level)
logging.getLogger("sqlalchemy.pool").setLevel(sql_log_level)

# Global scheduler
scheduler = AsyncIOScheduler()

# Global queue service and worker manager
queue_service = get_queue_service()
worker_manager = get_worker_manager(queue_service, num_workers=3)

# Global score aggregation service
aggregation_service = get_aggregation_service()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown tasks"""

    # Initialize Sentry
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            debug=settings.debug,
        )

    logger.info(
        f"Starting up {settings.service_name}({settings.service_version}) service..."
    )

    # Create database tables if they don't exist
    await create_tables()
    logger.info("Database tables ensured")

    # Auto-import skills if table is empty
    await auto_import_skills()

    # Add periodic ingestion job
    scheduler.add_job(
        run_slack_ingestion,
        CronTrigger.from_crontab(settings.ingestion_cron),
        id="slack_ingestion",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    # Add periodic queue cleanup job
    scheduler.add_job(
        queue_service.clear_completed_tasks,
        CronTrigger.from_crontab("37 * * * *"),  # Every hour at minute 37
        id="queue_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Scheduler started with cron: {settings.ingestion_cron}")
    logger.info("Queue cleanup scheduled for minute 37 of every hour")

    # Start background workers for message processing
    await worker_manager.start_workers()
    logger.info("Background workers started")

    yield

    logger.info(
        f"Shutting down {settings.service_name}({settings.service_version}) service..."
    )

    await worker_manager.stop_workers()
    logger.info("Background workers stopped")

    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


async def auto_import_skills():
    """Auto-import skills from JSON files if skills table is empty"""
    try:
        storage = StorageService()
        existing_skills = await storage.get_all_skills()
        if not existing_skills:
            skills_dir = Path("skills")
            if skills_dir.exists():
                logger.info("Skills table empty, importing from JSON files...")
                await import_taxonomy_files(skills_dir=skills_dir, validate_only=False)
                logger.info("Skills imported successfully")
            else:
                logger.warning(f"Skills directory not found: {skills_dir}")
        else:
            logger.info(f"Skills table already contains {len(existing_skills)} skills")
    except Exception as e:
        logger.error(f"Failed to auto-import skills: {e}")
        # Don't fail startup, just log the error


app = FastAPI(
    title="Truffle Ingestion Service",
    description="Automated message ingestion and expertise extraction",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint - service status"""
    queue_stats = await queue_service.get_queue_stats()
    return {
        "service": settings.service_name,
        "status": "running",
        "version": settings.service_version,
        "scheduler_active": scheduler.running if scheduler else False,
        "workers_active": worker_manager.is_running(),
        "queue_stats": queue_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    jobs = scheduler.get_jobs() if scheduler else []
    next_run = None

    if jobs:
        next_run = min(job.next_run_time for job in jobs if job.next_run_time)
        if next_run:
            next_run = next_run.isoformat()

    return {
        "status": "healthy",
        "scheduler_running": scheduler.running if scheduler else False,
        "jobs_count": len(jobs),
        "next_run": next_run,
        "settings": {
            "ingestion_cron": settings.ingestion_cron,
        },
    }


@app.get("/jobs")
async def list_jobs():
    """List all scheduled jobs"""
    if not scheduler:
        return {"jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
                "trigger": str(job.trigger),
            }
        )

    return {"jobs": jobs}


# Queue monitoring endpoints
@app.get("/queue/stats")
async def get_queue_stats():
    """Get current queue statistics"""
    return await queue_service.get_queue_stats()


@app.get("/workers/stats")
async def get_worker_stats():
    """Get worker statistics"""
    return {
        "workers": worker_manager.get_worker_stats(),
        "manager_running": worker_manager.is_running(),
    }


@app.get("/scores/stats")
async def get_aggregation_stats():
    """Get statistics about score aggregation"""
    try:
        stats = await aggregation_service.get_aggregation_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get aggregation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/queue/clear")
async def clear_completed_tasks():
    """Manually clear completed tasks from queue"""
    try:
        count = await queue_service.clear_completed_tasks()
        return {"cleared_tasks": count, "status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear completed tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/database/reset")
async def reset_database(import_skills: bool = True):
    """Reset database by dropping and recreating all tables"""
    try:
        logger.info("Starting database reset via web API")

        # Drop all tables
        logger.info("Dropping all database tables...")
        await drop_tables()
        logger.info("All tables dropped")

        # Create tables
        logger.info("Creating database tables...")
        await create_tables()
        logger.info("Database tables created")

        # Import skills if requested
        if import_skills:
            logger.info("Importing skills from JSON files...")
            await auto_import_skills()
            logger.info("Skills imported")

        return {
            "status": "success",
            "message": "Database reset completed",
            "skills_imported": import_skills,
        }

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Database reset failed: {str(e)}"
        ) from e


async def _background_slack_import():
    """Background task for Slack import"""
    try:
        logger.info("Starting background Slack import")
        await run_slack_ingestion()
        logger.info("Background Slack import completed successfully")
    except Exception as e:
        logger.error(f"Background Slack import failed: {e}", exc_info=True)


@app.post("/slack/reimport")
async def trigger_full_slack_import(background_tasks: BackgroundTasks):
    """Trigger full historical Slack import (30 days)"""
    try:
        logger.info("Scheduling full Slack reimport via web API")

        storage = StorageService()
        is_empty = await storage.is_database_empty()

        # Schedule the import as a background task
        background_tasks.add_task(_background_slack_import)

        return {
            "status": "accepted",
            "message": "Full Slack import scheduled and starting in background",
            "was_empty_database": is_empty,
            "note": (
                "Import is running in background. "
                "Check /queue/stats and /workers/stats for progress."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to schedule Slack reimport: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule Slack reimport: {str(e)}"
        ) from e


async def _background_reset_and_import():
    """Background task for database reset and Slack import"""
    try:
        logger.info("Starting background database reset and import")

        # Reset database
        logger.info("Resetting database...")
        await drop_tables()
        await create_tables()
        await auto_import_skills()
        logger.info("Database reset completed")

        # Import Slack history
        logger.info("Starting Slack import...")
        await run_slack_ingestion()

        logger.info("Background reset and import completed successfully")
    except Exception as e:
        logger.error(f"Background reset and import failed: {e}", exc_info=True)


@app.post("/database/reset-and-reimport")
async def reset_and_reimport_all(background_tasks: BackgroundTasks):
    """Reset database and trigger full Slack history import"""
    try:
        logger.info("Scheduling full database reset and reimport via web API")

        # Schedule the reset and import as a background task
        background_tasks.add_task(_background_reset_and_import)

        return {
            "status": "accepted",
            "message": (
                "Database reset and Slack import scheduled and starting in background"
            ),
            "note": (
                "Reset and import are running in background. "
                "Check /queue/stats and /workers/stats for progress."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to schedule reset and reimport: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule reset and reimport: {str(e)}"
        ) from e


class ChannelImportRequest(BaseModel):
    channel_id: str
    channel_name: str
    import_history_days: int = 30


@app.post("/import/channel")
async def import_single_channel(
    request: ChannelImportRequest, background_tasks: BackgroundTasks
):
    """Import messages from a specific channel (triggered when bot is added)"""
    try:
        logger.info(
            f"Received import request for channel "
            f"#{request.channel_name} ({request.channel_id})"
        )

        # Schedule the import as a background task
        background_tasks.add_task(
            _background_channel_import,
            request.channel_id,
            request.channel_name,
            request.import_history_days,
        )

        return {
            "status": "accepted",
            "message": f"Channel import for #{request.channel_name} scheduled",
            "channel_id": request.channel_id,
            "import_history_days": request.import_history_days,
            "note": "Import is running in background. Check logs for progress.",
        }

    except Exception as e:
        logger.error(f"Failed to schedule channel import: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule channel import: {str(e)}"
        ) from e


async def _background_channel_import(
    channel_id: str, channel_name: str, import_history_days: int
):
    """Background task for importing a specific channel"""
    try:
        logger.info(f"Starting background import for channel #{channel_name}")

        slack_service = SlackService()
        storage = StorageService()
        queue_service = get_queue_service()

        # Get workspace users (needed for message processing)
        users = await slack_service.get_workspace_users()
        await storage.upsert_users(users)

        messages_enqueued = 0

        # Reset batch counter for this channel
        slack_service.reset_batch_counter()

        # Add initial delay to respect rate limits when triggered by bot join
        delay = settings.slack_channel_delay_seconds
        logger.info(
            f"Waiting {delay} seconds before starting channel import "
            f"to respect rate limits..."
        )
        await asyncio.sleep(delay)

        logger.info(
            f"Importing messages from #{channel_name} (last {import_history_days} days)"
        )

        # Get messages from the channel
        async for message in slack_service.get_recent_messages(
            channel_id,
            since_hours=import_history_days * 24,  # Convert days to hours
        ):
            # Replace user mentions for better text processing
            if message.get("text"):
                message["text"] = slack_service.replace_user_mentions(
                    message["text"], users
                )

            # Create channel info for the queue
            channel_info = {"id": channel_id, "name": channel_name}

            # Enqueue message for background processing
            await queue_service.enqueue_message(message, channel_info, users)
            messages_enqueued += 1

            # Progress logging
            if messages_enqueued % 50 == 0:
                logger.info(
                    f"Enqueued {messages_enqueued} messages from #{channel_name}..."
                )
                await asyncio.sleep(0.5)  # Brief pause

        logger.info(
            f"✅ Channel import completed for #{channel_name}: "
            f"{messages_enqueued} messages enqueued"
        )

    except Exception as e:
        logger.error(
            f"Background channel import failed for #{channel_name}: {e}", exc_info=True
        )


if __name__ == "__main__":
    import uvicorn

    logger.info(
        f"Starting {settings.service_name}({settings.service_version}) on "
        f"{settings.ingestor_host}:{settings.ingestor_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.ingestor_host,
        port=settings.ingestor_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
