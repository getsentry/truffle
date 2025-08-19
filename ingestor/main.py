import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import FastAPI

from config import settings
from database import create_tables
from schedulers.slack_ingestion import run_slack_ingestion
from scripts.import_taxonomy import import_taxonomy_files
from services.queue_service import get_queue_service
from services.skill_service import SkillService
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for startup/shutdown tasks"""

    # Startup: Initialize database and start scheduler
    logger.info("Starting Truffle Ingestion Service...")

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

    scheduler.start()
    logger.info(f"Scheduler started with cron: {settings.ingestion_cron}")

    # Start background workers for message processing
    await worker_manager.start_workers()
    logger.info("Background workers started")

    yield

    # Shutdown: Stop workers and scheduler
    await worker_manager.stop_workers()
    logger.info("Background workers stopped")

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
    queue_stats = await queue_service.get_queue_stats()
    return {
        "service": "Truffle Slack Ingestion",
        "status": "running",
        "scheduler_active": scheduler.running if scheduler else False,
        "workers_active": worker_manager.is_running(),
        "queue_stats": queue_stats,
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


@app.post("/reload-skills")
async def reload_skills():
    """Force reload skills from database"""
    skill_service = SkillService()
    await skill_service.reload_skills()
    return {"message": "Skills reloaded successfully"}


@app.post("/import-skills")
async def import_skills(validate_only: bool = False):
    """Import skills from JSON files in skills/ directory"""
    try:
        skills_dir = Path("skills")
        if not skills_dir.exists():
            return {"error": "Skills directory not found", "path": str(skills_dir)}

        await import_taxonomy_files(skills_dir=skills_dir, validate_only=validate_only)

        # Reload skills in memory after successful import
        if not validate_only:
            skill_service = SkillService()
            await skill_service.reload_skills()

        action = "validated" if validate_only else "imported and reloaded"
        return {"message": f"Skills {action} successfully"}

    except Exception as e:
        return {"error": str(e)}


# Queue monitoring endpoints
@app.get("/queue/stats")
async def get_queue_stats():
    """Get current queue statistics"""
    return await queue_service.get_queue_stats()


@app.get("/queue/tasks")
async def get_recent_tasks(limit: int = 50):
    """Get recent tasks for monitoring"""
    return {"tasks": await queue_service.get_recent_tasks(limit)}


@app.get("/workers/stats")
async def get_worker_stats():
    """Get worker statistics"""
    return {
        "workers": worker_manager.get_worker_stats(),
        "manager_running": worker_manager.is_running()
    }


@app.post("/queue/clear-completed")
async def clear_completed_tasks():
    """Clear completed tasks to free memory"""
    count = await queue_service.clear_completed_tasks()
    return {"message": f"Cleared {count} completed tasks"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
