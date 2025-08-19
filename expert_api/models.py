"""Data models for Expert API"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkillSearchRequest(BaseModel):
    """Request model for skill-based expert search"""
    skills: list[str]
    limit: int = Field(default=10, ge=1, le=50)
    include_confidence: bool = True
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExpertResult(BaseModel):
    """Individual expert search result"""
    user_id: str
    user_name: str | None = None
    display_name: str | None = None

    # Expertise information
    skills: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)

    # Metadata
    last_active: datetime | None = None
    total_messages: int = Field(default=0, ge=0)


class ExpertSearchResponse(BaseModel):
    """Response model for expert search"""
    query: SkillSearchRequest
    results: list[ExpertResult]
    total_found: int = Field(ge=0)
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Search metadata
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    search_strategy: str = "skill_based"


class SkillInfo(BaseModel):
    """Information about a skill"""
    key: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str | None = None
    expert_count: int = Field(default=0, ge=0)


class SkillsResponse(BaseModel):
    """Response model for skills listing"""
    skills: list[SkillInfo]
    total_count: int = Field(ge=0)
    categories: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    timestamp: str
    database_connected: bool = False
    total_experts: int = Field(default=0, ge=0)
    total_skills: int = Field(default=0, ge=0)
