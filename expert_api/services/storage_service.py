"""Storage service for Expert API - Read-only database operations"""

import logging
from typing import Any

from sqlalchemy import func, select

from database import AsyncSessionLocal, ExpertiseEvidence, Skill, User, UserSkillScore

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

    async def find_experts_by_skills(
        self, skill_keys: list[str], limit: int = 10, min_confidence: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Find experts based on skill keys.

        Returns a list of expert results with aggregated scores for users
        who have expertise in the requested skills.
        """
        try:
            async with AsyncSessionLocal() as session:
                # First, get skill IDs for the requested skill keys
                skill_query = select(Skill.skill_id, Skill.skill_key).where(
                    Skill.skill_key.in_(skill_keys)
                )
                skill_result = await session.execute(skill_query)
                skill_map = {
                    row.skill_key: row.skill_id for row in skill_result.fetchall()
                }
                found_skill_ids = list(skill_map.values())
                if not found_skill_ids:
                    logger.warning(f"No skills found for keys: {skill_keys}")
                    return []

                # Query UserSkillScore with User join for experts with these skills
                # Aggregate scores for users who have multiple matching skills
                query = (
                    select(
                        User.user_id,
                        User.slack_id,
                        User.display_name,
                        func.sum(UserSkillScore.score).label("total_score"),
                        func.sum(UserSkillScore.evidence_count).label("total_evidence"),
                        func.count(UserSkillScore.skill_id).label("matching_skills_count"),
                        func.avg(UserSkillScore.score).label("avg_score")
                    )
                    .select_from(UserSkillScore)
                    .join(User, UserSkillScore.user_id == User.user_id)
                    .where(UserSkillScore.skill_id.in_(found_skill_ids))
                    .group_by(User.user_id, User.slack_id, User.display_name)
                    .having(func.avg(UserSkillScore.score) >= min_confidence)
                    .order_by(func.sum(UserSkillScore.score).desc())
                    .limit(limit)
                )

                result = await session.execute(query)
                expert_rows = result.fetchall()

                # Build expert results
                experts = []
                for row in expert_rows:
                    # Get the specific skills this user has from our requested list
                    user_skills_query = (
                        select(Skill.skill_key, UserSkillScore.score)
                        .select_from(UserSkillScore)
                        .join(Skill, UserSkillScore.skill_id == Skill.skill_id)
                        .where(
                            UserSkillScore.user_id == row.user_id,
                            UserSkillScore.skill_id.in_(found_skill_ids)
                        )
                    )

                    user_skills_result = await session.execute(user_skills_query)
                    user_skills = user_skills_result.fetchall()

                    expert = {
                        "user_id": row.slack_id,  # Use slack_id as external user_id
                        "user_name": row.slack_id.lower(),  # Generate from slack_id
                        "display_name": row.display_name,
                        "skills": [skill.skill_key for skill in user_skills],
                        "confidence_score": float(row.avg_score),  # Average score
                        "evidence_count": int(row.total_evidence),
                        "total_messages": int(row.total_evidence),  # Use evidence count
                        "matching_skills_count": int(row.matching_skills_count),
                        "total_score": float(row.total_score)
                    }
                    experts.append(expert)

                logger.info(
                    f"Found {len(experts)} experts for skills {skill_keys} "
                    f"(min_confidence={min_confidence})"
                )
                return experts

        except Exception as e:
            logger.error(f"Error finding experts by skills: {e}")
            return []
