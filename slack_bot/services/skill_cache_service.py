"""Skill cache service for fast skill lookups from database"""

import asyncio
import logging
from datetime import datetime, timedelta

import sentry_sdk

from .expert_api_client import ExpertAPIClient, SkillInfo

logger = logging.getLogger(__name__)


class SkillCacheService:
    """
    Caches skills from Expert API for fast text matching.

    Maintains an in-memory cache of skills with their aliases
    for efficient skill extraction from natural language text.
    """

    def __init__(self, expert_api_client: ExpertAPIClient, cache_ttl_minutes: int = 60):
        self.expert_api_client = expert_api_client
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)

        # Cache storage
        self._skills: list[SkillInfo] = []
        self._skill_names: set[str] = set()
        self._skill_aliases: set[str] = set()
        self._all_skill_terms: set[str] = set()  # Combined names + aliases
        self._domains: list[str] = []
        self._last_refresh: datetime | None = None
        self._refresh_lock = asyncio.Lock()

        logger.info("SkillCacheService initialized")

    async def get_all_skill_terms(self) -> set[str]:
        """Get all skill terms (names + aliases) for text matching"""
        await self._ensure_cache_fresh()
        return self._all_skill_terms.copy()

    async def get_skills(self) -> list[SkillInfo]:
        """Get all cached skills"""
        await self._ensure_cache_fresh()
        return self._skills.copy()

    async def get_domains(self) -> list[str]:
        """Get all available domains"""
        await self._ensure_cache_fresh()
        return self._domains.copy()

    @sentry_sdk.trace
    async def get_skill_by_term(self, term: str) -> SkillInfo | None:
        """Find skill by name or alias (case-insensitive)"""
        await self._ensure_cache_fresh()
        term_lower = term.lower()

        for skill in self._skills:
            # Check skill name
            if skill.name.lower() == term_lower:
                return skill

            # Check aliases
            if hasattr(skill, "aliases") and skill.aliases:
                for alias in skill.aliases:
                    if alias.lower() == term_lower:
                        return skill

        return None

    @sentry_sdk.trace
    async def refresh_cache(self) -> bool:
        """Force refresh the skill cache from Expert API"""
        async with self._refresh_lock:
            try:
                logger.info("Refreshing skill cache from Expert API...")

                # Fetch skills from Expert API
                skills_response = await self.expert_api_client.list_skills()

                # Update cache
                self._skills = skills_response.skills
                self._domains = skills_response.domains
                self._skill_names = set()
                self._skill_aliases = set()
                self._all_skill_terms = set()

                # Build lookup sets
                for skill in self._skills:
                    skill_name_lower = skill.name.lower()
                    self._skill_names.add(skill_name_lower)
                    self._all_skill_terms.add(skill_name_lower)

                    # Add aliases if they exist
                    if hasattr(skill, "aliases") and skill.aliases:
                        for alias in skill.aliases:
                            alias_lower = alias.lower()
                            self._skill_aliases.add(alias_lower)
                            self._all_skill_terms.add(alias_lower)

                self._last_refresh = datetime.now()

                logger.info(
                    f"Skill cache refreshed successfully: "
                    f"{len(self._skills)} skills, "
                    f"{len(self._all_skill_terms)} total terms, "
                    f"{len(self._domains)} domains"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to refresh skill cache: {e}")
                return False

    async def _ensure_cache_fresh(self):
        """Ensure cache is fresh, refresh if needed"""
        if self._needs_refresh():
            await self.refresh_cache()

    def _needs_refresh(self) -> bool:
        """Check if cache needs refreshing"""
        if self._last_refresh is None:
            return True

        age = datetime.now() - self._last_refresh
        return age > self.cache_ttl

    def get_cache_stats(self) -> dict[str, any]:
        """Get cache statistics for debugging"""
        return {
            "skills_count": len(self._skills),
            "skill_names_count": len(self._skill_names),
            "skill_aliases_count": len(self._skill_aliases),
            "total_terms_count": len(self._all_skill_terms),
            "domains_count": len(self._domains),
            "last_refresh": (
                self._last_refresh.isoformat() if self._last_refresh else None
            ),
            "cache_age_minutes": (
                (datetime.now() - self._last_refresh).total_seconds() / 60
                if self._last_refresh
                else None
            ),
            "needs_refresh": self._needs_refresh(),
        }
