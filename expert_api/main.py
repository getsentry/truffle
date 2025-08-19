"""Expert API Service - Fast, dedicated expert search API"""

import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "expert_api",
        "timestamp": datetime.utcnow().isoformat()
    }


# Expert search endpoints will be added here when we move the code
# from ingestor service


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
