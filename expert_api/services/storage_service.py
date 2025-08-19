"""Storage service for Expert API - Read-only database operations"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, ExpertiseEvidence, Skill, User

logger = logging.getLogger(__name__)


class StorageService:
    """Read-only storage service for Expert API"""

    def __init__(self):
        pass

    async def get_all_skills(self) -> list[Skill]:
        """Get all skills from database"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Skill))
            return list(result.scalars().all())

    async def get_skill_by_key(self, skill_key: str) -> Skill | None:
        """Get a skill by its key"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Skill).where(Skill.skill_key == skill_key)
            )
            return result.scalar_one_or_none()

    async def get_skills_by_domain(self, domain: str) -> list[Skill]:
        """Get all skills in a specific domain"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Skill).where(Skill.domain == domain)
            )
            return list(result.scalars().all())

    async def get_skill_domains(self) -> list[str]:
        """Get all unique skill domains"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Skill.domain).distinct()
            )
            return [row[0] for row in result.fetchall()]

    async def health_check(self) -> dict[str, Any]:
        """Perform database health check"""
        try:
            async with AsyncSessionLocal() as session:
                # Try to count skills and users
                skill_result = await session.execute(select(Skill))
                skills_count = len(list(skill_result.scalars().all()))

                user_result = await session.execute(select(User))
                users_count = len(list(user_result.scalars().all()))

                evidence_result = await session.execute(select(ExpertiseEvidence))
                evidence_count = len(list(evidence_result.scalars().all()))

                return {
                    "database_connected": True,
                    "total_skills": skills_count,
                    "total_users": users_count,
                    "total_evidence": evidence_count,
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "database_connected": False,
                "error": str(e),
                "total_skills": 0,
                "total_users": 0,
                "total_evidence": 0,
            }
