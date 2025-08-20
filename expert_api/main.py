"""Expert API Service - Fast, dedicated expert search API"""

import json
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import (
    ExpertResult,
    ExpertSearchResponse,
    HealthResponse,
    SkillInfo,
    SkillSearchRequest,
    SkillsResponse,
)
from services import StorageService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize storage service
storage_service = StorageService()

# Create FastAPI app
app = FastAPI(
    title="Truffle Expert Search API",
    description="Dedicated service for finding experts by skills and expertise",
    version="1.0.0",
)

# Add CORS middleware for cross-service communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.ingestor_url,
        settings.slack_bot_url,
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
        "service": "Truffle Expert Search API",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "description": "Dedicated expert search and skill discovery service"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    health_data = await storage_service.health_check()

    return HealthResponse(
        status="healthy" if health_data["database_connected"] else "unhealthy",
        service="expert_api",
        timestamp=datetime.utcnow().isoformat(),
        database_connected=health_data["database_connected"],
        total_experts=health_data["total_users"],
        total_skills=health_data["total_skills"],
    )


@app.post("/experts/search", response_model=ExpertSearchResponse)
async def search_experts(request: SkillSearchRequest):
    """Search for experts by skills"""
    import time
    start_time = time.time()

    logger.info(f"Searching for experts with skills: {request.skills}")

    # Query database for actual experts
    try:
        expert_data = await storage_service.find_experts_by_skills(
            skill_keys=request.skills,
            limit=request.limit,
            min_confidence=request.min_confidence
        )

        # Convert to ExpertResult objects
        expert_results = []
        for data in expert_data:
            expert_result = ExpertResult(
                user_id=data["user_id"],
                user_name=data["user_name"],
                display_name=data["display_name"],
                skills=data["skills"],
                confidence_score=data["confidence_score"],
                evidence_count=data["evidence_count"],
                total_messages=data["total_messages"]
            )
            expert_results.append(expert_result)

        limited_results = expert_results

    except Exception as e:
        logger.error(f"Error querying experts from database: {e}")
        # Return empty results on error
        limited_results = []

    processing_time = (time.time() - start_time) * 1000

    return ExpertSearchResponse(
        query=request,
        results=limited_results,
        total_found=len(limited_results),
        processing_time_ms=processing_time,
        search_strategy="database_skill_based"
    )


@app.get("/skills", response_model=SkillsResponse)
async def list_skills():
    """List all available skills from database"""
    try:
        # Get skills from database
        db_skills = await storage_service.get_all_skills()

        # Convert to API models
        skills = []
        for db_skill in db_skills:
            # Parse aliases from JSON string
            aliases = []
            if db_skill.aliases:
                try:
                    aliases = json.loads(db_skill.aliases)
                except (json.JSONDecodeError, TypeError):
                    aliases = []

            skills.append(SkillInfo(
                key=db_skill.skill_key,
                name=db_skill.name,
                domain=db_skill.domain,
                aliases=aliases,
                expert_count=0  # TODO: Calculate from expertise evidence
            ))

        # Get unique domains
        domains = list(set(skill.domain for skill in skills if skill.domain))

        logger.info(f"Retrieved {len(skills)} skills from database")

        return SkillsResponse(
            skills=skills,
            total_count=len(skills),
            domains=sorted(domains)
        )

    except Exception as e:
        logger.error(f"Error retrieving skills from database: {e}")
        # Return empty response on error
        return SkillsResponse(
            skills=[],
            total_count=0,
            domains=[]
        )


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting Expert API on "
        f"{settings.expert_api_host}:{settings.expert_api_port}"
    )
    uvicorn.run(
        "main:app",
        host=settings.expert_api_host,
        port=settings.expert_api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
