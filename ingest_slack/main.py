import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import FastAPI

from config import settings
from database import create_tables
from schedulers.slack_ingestion import run_slack_ingestion

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown tasks"""

    # Startup: Initialize database and start scheduler
    logger.info("Starting Truffle Ingestion Service...")

    # Create database tables if they don't exist
    await create_tables()
    logger.info("Database tables ensured")

    # Add periodic ingestion job
    scheduler.add_job(
        run_slack_ingestion,
        CronTrigger.from_crontab(settings.ingestion_cron),  # Every 15 min
        id="slack_ingestion",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    scheduler.start()
    logger.info(f"Scheduler started with cron: {settings.ingestion_cron}")

    yield

    # Shutdown: Stop the scheduler
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Truffle Slack Ingestion Service",
    description="Automated Slack message ingestion and expertise extraction",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint with service status"""
    return {
        "service": "Truffle Slack Ingestion",
        "status": "running",
        "scheduler_active": scheduler.running if scheduler else False,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/trigger-ingestion")
async def trigger_manual_ingestion():
    """Manual trigger for ingestion - useful for testing/debugging"""
    logger.info("Manual ingestion triggered via API")

    try:
        await run_slack_ingestion()
        return {"message": "Ingestion completed successfully"}
    except Exception as e:
        logger.error(f"Manual ingestion failed: {e}")
        return {"error": f"Ingestion failed: {str(e)}"}, 500


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
