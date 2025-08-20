import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import FastAPI, HTTPException

from config import settings
from database import create_tables
from schedulers.slack_ingestion import run_slack_ingestion
from scripts.import_taxonomy import import_taxonomy_files
from services.queue_service import get_queue_service
from services.score_aggregation_service import get_aggregation_service
from services.storage_service import StorageService
from workers import get_worker_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
            "extract_skills": settings.extract_skills,
            "classify_expertise": settings.classify_expertise,
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queue/clear")
async def clear_completed_tasks():
    """Manually clear completed tasks from queue"""
    try:
        count = await queue_service.clear_completed_tasks()
        return {"cleared_tasks": count, "status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear completed tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
