"""Expert API Service - Fast, dedicated expert search API"""

import json
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import (
    ExpertSearchResponse,
    ExpertResult,
    HealthResponse,
    SkillSearchRequest,
    SkillsResponse,
    SkillInfo,
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

    # TODO: Replace with actual database query
    # For now, return mock data for testing
    mock_results = []

    if "python" in [skill.lower() for skill in request.skills]:
        mock_results.append(ExpertResult(
            user_id="U123PYTHON",
            user_name="alice.python",
            display_name="Alice Python",
            skills=["python", "django", "fastapi"],
            confidence_score=0.95,
            evidence_count=15,
            total_messages=42
        ))

    if "react" in [skill.lower() for skill in request.skills]:
        mock_results.append(ExpertResult(
            user_id="U456REACT",
            user_name="bob.frontend",
            display_name="Bob React",
            skills=["react", "typescript", "javascript"],
            confidence_score=0.88,
            evidence_count=12,
            total_messages=35
        ))

    if "kubernetes" in [skill.lower() for skill in request.skills]:
        mock_results.append(ExpertResult(
            user_id="U789K8S",
            user_name="charlie.devops",
            display_name="Charlie K8s",
            skills=["kubernetes", "docker", "terraform"],
            confidence_score=0.92,
            evidence_count=8,
            total_messages=28
        ))

    # Apply confidence filter
    filtered_results = [
        r for r in mock_results
        if r.confidence_score >= request.min_confidence
    ]

    # Apply limit
    limited_results = filtered_results[:request.limit]

    processing_time = (time.time() - start_time) * 1000

    return ExpertSearchResponse(
        query=request,
        results=limited_results,
        total_found=len(filtered_results),
        processing_time_ms=processing_time,
        search_strategy="mock_skill_based"
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
                category=db_skill.domain,
                aliases=aliases,
                expert_count=0  # TODO: Calculate from expertise evidence
            ))

        # Get unique categories
        categories = list(set(skill.category for skill in skills if skill.category))

        logger.info(f"Retrieved {len(skills)} skills from database")

        return SkillsResponse(
            skills=skills,
            total_count=len(skills),
            categories=sorted(categories)
        )

    except Exception as e:
        logger.error(f"Error retrieving skills from database: {e}")
        # Return empty response on error
        return SkillsResponse(
            skills=[],
            total_count=0,
            categories=[]
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
