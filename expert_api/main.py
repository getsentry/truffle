"""Expert API Service - Fast, dedicated expert search API"""

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

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    return HealthResponse(
        status="healthy",
        service="expert_api",
        timestamp=datetime.utcnow().isoformat(),
        database_connected=False,  # TODO: Check actual database connection
        total_experts=0,  # TODO: Get from database
        total_skills=0,   # TODO: Get from database
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
    """List all available skills"""

    # TODO: Replace with actual database query
    mock_skills = [
        SkillInfo(key="python", name="Python", category="programming"),
        SkillInfo(key="react", name="React", category="frontend"),
        SkillInfo(key="kubernetes", name="Kubernetes", category="devops"),
        SkillInfo(key="docker", name="Docker", category="devops"),
        SkillInfo(key="typescript", name="TypeScript", category="programming"),
        SkillInfo(key="django", name="Django", category="backend"),
        SkillInfo(key="fastapi", name="FastAPI", category="backend"),
    ]

    categories = list(set(skill.category for skill in mock_skills if skill.category))

    return SkillsResponse(
        skills=mock_skills,
        total_count=len(mock_skills),
        categories=sorted(categories)
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
