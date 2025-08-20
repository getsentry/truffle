import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from config import settings
from database import create_tables
from schedulers.slack_ingestion import run_slack_ingestion
from scripts.import_taxonomy import import_taxonomy_files
from services.expert_search_service import ExpertQuery, ExpertSearchService, SortBy
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

# Global expert search service
expert_search_service = ExpertSearchService()

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
            debug=True,
        )

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


# Pydantic models for expert search API
class ExpertSearchRequest(BaseModel):
    """Request model for expert search"""

    query: str
    min_confidence: float = 0.3
    min_evidence_count: int = 1
    time_window_days: int = 180
    include_negative: bool = False
    exclude_neutral: bool = True
    sort_by: str = "score"  # score, recent, evidence_count, alphabetical
    limit: int = 10
    offset: int = 0


class MultiSkillSearchRequest(BaseModel):
    """Request model for multi-skill expert search"""

    skills: list[str]
    operator: str = "OR"  # AND, OR
    min_confidence: float = 0.3
    min_evidence_count: int = 1
    time_window_days: int = 180
    sort_by: str = "score"
    limit: int = 10


# Expert Search API Endpoints
@app.get("/experts/skill/{skill_key}")
async def get_experts_by_skill_key(
    skill_key: str,
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    min_evidence_count: int = Query(1, ge=1),
    time_window_days: int = Query(180, ge=0),
    include_negative: bool = Query(False),
    sort_by: str = Query("score", regex="^(score|recent|evidence_count|alphabetical)$"),
    limit: int = Query(10, ge=1, le=100),
):
    """Get experts for a specific skill by skill key"""
    try:
        query = ExpertQuery(
            min_confidence=min_confidence,
            min_evidence_count=min_evidence_count,
            time_window_days=time_window_days,
            include_negative=include_negative,
            sort_by=SortBy(sort_by),
            limit=limit,
        )

        experts = await expert_search_service.search_experts_by_skill_key(
            skill_key, query
        )

        return {
            "skill_key": skill_key,
            "total_found": len(experts),
            "results": [expert.to_dict() for expert in experts],
            "query_params": {
                "min_confidence": min_confidence,
                "min_evidence_count": min_evidence_count,
                "time_window_days": time_window_days,
                "sort_by": sort_by,
            },
        }
    except Exception as e:
        logger.error(f"Error searching experts by skill key {skill_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experts/search")
async def search_experts(request: ExpertSearchRequest):
    """Search experts using natural language query with fuzzy matching"""
    try:
        query = ExpertQuery(
            min_confidence=request.min_confidence,
            min_evidence_count=request.min_evidence_count,
            time_window_days=request.time_window_days,
            include_negative=request.include_negative,
            exclude_neutral=request.exclude_neutral,
            sort_by=SortBy(request.sort_by),
            limit=request.limit,
            offset=request.offset,
        )

        # Try multiple search strategies
        experts = []

        # 1. Try exact skill name match first
        name_experts = await expert_search_service.search_experts_by_skill_name(
            request.query, query
        )
        if name_experts:
            experts.extend(name_experts)

        # 2. If no exact matches, try fuzzy search
        if not experts:
            fuzzy_experts = await expert_search_service.search_experts_fuzzy(
                request.query, query
            )
            experts.extend(fuzzy_experts)

        # Remove duplicates (by slack_id + skill_key combination)
        seen = set()
        unique_experts = []
        for expert in experts:
            key = (expert.slack_id, expert.skill_key)
            if key not in seen:
                seen.add(key)
                unique_experts.append(expert)

        return {
            "query": request.query,
            "search_strategy": "name_match" if name_experts else "fuzzy_match",
            "total_found": len(unique_experts),
            "results": [expert.to_dict() for expert in unique_experts[: request.limit]],
            "query_params": request.dict(),
        }
    except Exception as e:
        logger.error(f"Error in expert search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/experts/skills")
async def search_experts_multi_skill(request: MultiSkillSearchRequest):
    """Search experts who know multiple skills"""
    try:
        if not request.skills:
            raise HTTPException(
                status_code=400, detail="At least one skill must be provided"
            )

        query = ExpertQuery(
            min_confidence=request.min_confidence,
            min_evidence_count=request.min_evidence_count,
            time_window_days=request.time_window_days,
            sort_by=SortBy(request.sort_by),
            limit=request.limit
            * len(request.skills),  # Get more results for combination
        )

        # Search for each skill
        all_results = {}  # slack_id -> {skill_key -> ExpertResult}

        for skill in request.skills:
            # Try fuzzy search for each skill
            skill_experts = await expert_search_service.search_experts_fuzzy(
                skill, query
            )

            for expert in skill_experts:
                if expert.slack_id not in all_results:
                    all_results[expert.slack_id] = {}
                all_results[expert.slack_id][expert.skill_key] = expert

        # Apply AND/OR logic
        if request.operator.upper() == "AND":
            # User must have expertise in ALL skills
            multi_skill_experts = []
            for slack_id, skills_dict in all_results.items():
                if len(skills_dict) >= len(request.skills):
                    # Calculate combined score (average)
                    total_score = sum(
                        expert.expertise_score for expert in skills_dict.values()
                    )
                    avg_score = total_score / len(skills_dict)

                    # Use the first expert as template, update with combined info
                    first_expert = next(iter(skills_dict.values()))
                    first_expert.expertise_score = avg_score
                    first_expert.skill_name = f"Multiple Skills ({len(skills_dict)})"
                    multi_skill_experts.append(first_expert)

            # Sort by combined score
            multi_skill_experts.sort(key=lambda x: x.expertise_score, reverse=True)
            final_results = multi_skill_experts[: request.limit]
        else:
            # OR logic - user has expertise in ANY skill
            all_experts = []
            for skills_dict in all_results.values():
                all_experts.extend(skills_dict.values())

            # Sort and limit
            all_experts.sort(key=lambda x: x.expertise_score, reverse=True)
            final_results = all_experts[: request.limit]

        return {
            "skills": request.skills,
            "operator": request.operator,
            "total_found": len(final_results),
            "results": [expert.to_dict() for expert in final_results],
            "query_params": request.dict(),
        }
    except Exception as e:
        logger.error(f"Error in multi-skill search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/skills/suggest")
async def suggest_skills(
    q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)
):
    """Get skill suggestions for autocomplete"""
    try:
        suggestions = await expert_search_service.get_skill_suggestions(q, limit)
        return {"query": q, "suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting skill suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Score aggregation endpoints
@app.post("/scores/aggregate")
async def aggregate_scores():
    """Manually trigger full score aggregation from evidence"""
    try:
        logger.info("Manual score aggregation triggered via API")
        result = await aggregation_service.aggregate_all_scores()
        return result
    except Exception as e:
        logger.error(f"Score aggregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scores/stats")
async def get_aggregation_stats():
    """Get statistics about score aggregation"""
    try:
        stats = await aggregation_service.get_aggregation_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get aggregation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting Truffle Ingestor Service on "
        f"{settings.ingestor_host}:{settings.ingestor_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.ingestor_host,
        port=settings.ingestor_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
