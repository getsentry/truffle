"""HTTP client for Expert API service"""

import logging
from typing import Any

import httpx
import sentry_sdk
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExpertAPIError(Exception):
    """Exception raised when Expert API calls fail"""

    pass


class ExpertResult(BaseModel):
    """Expert search result from API"""

    user_id: str
    user_name: str | None = None
    display_name: str | None = None
    skills: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    total_messages: int = Field(default=0, ge=0)


class ExpertSearchResponse(BaseModel):
    """Response from expert search API"""

    results: list[ExpertResult]
    total_found: int = Field(ge=0)
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    search_strategy: str = "skill_based"


class SkillInfo(BaseModel):
    """Skill information from API"""

    key: str
    name: str
    domain: str | None = None
    aliases: list[str] = Field(default_factory=list)
    expert_count: int = Field(default=0, ge=0)


class SkillsResponse(BaseModel):
    """Response from skills listing API"""

    skills: list[SkillInfo]
    total_count: int = Field(ge=0)
    domains: list[str] = Field(default_factory=list)


class ExpertAPIClient:
    """HTTP client for Expert API service"""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Create HTTP client with sensible defaults
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": "truffle-slack-bot/1.0.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        logger.info(f"Expert API client initialized for {self.base_url}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def health_check(self) -> dict[str, Any]:
        """Check Expert API health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Expert API: {e}")
            raise ExpertAPIError(f"Connection failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Expert API health check failed: {e}")
            raise ExpertAPIError(f"Health check failed: {e.response.status_code}")

    @sentry_sdk.trace
    async def search_experts(
        self, skills: list[str], limit: int = 10, min_confidence: float = 0.0
    ) -> ExpertSearchResponse:
        """Search for experts by skills"""
        try:
            payload = {
                "skills": skills,
                "limit": limit,
                "min_confidence": min_confidence,
                "include_confidence": True,
            }

            logger.info(f"Searching experts for skills: {skills}")

            response = await self.client.post(
                f"{self.base_url}/experts/search", json=payload
            )
            response.raise_for_status()

            data = response.json()
            result = ExpertSearchResponse(**data)

            logger.info(
                f"Found {result.total_found} experts for {skills} "
                f"(returned {len(result.results)})"
            )

            return result

        except httpx.RequestError as e:
            logger.error(f"Failed to search experts: {e}")
            raise ExpertAPIError(f"Search request failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Expert search failed: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                raise ExpertAPIError(f"Search failed: {error_detail}")
            except Exception:
                raise ExpertAPIError(f"Search failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error during expert search: {e}")
            raise ExpertAPIError(f"Unexpected error: {e}")

    @sentry_sdk.trace
    async def list_skills(self) -> SkillsResponse:
        """Get list of available skills"""
        try:
            response = await self.client.get(f"{self.base_url}/skills")
            response.raise_for_status()

            data = response.json()
            result = SkillsResponse(**data)

            logger.info(f"Retrieved {result.total_count} skills")
            return result

        except httpx.RequestError as e:
            logger.error(f"Failed to get skills: {e}")
            raise ExpertAPIError(f"Skills request failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Skills request failed: {e.response.status_code}")
            raise ExpertAPIError(f"Skills request failed: {e.response.status_code}")

    async def is_available(self) -> bool:
        """Check if Expert API is available and responding"""
        try:
            await self.health_check()
            return True
        except ExpertAPIError:
            return False

    def __repr__(self) -> str:
        return f"ExpertAPIClient(base_url='{self.base_url}')"
