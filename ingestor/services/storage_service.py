from datetime import date
from typing import Any

import sentry_sdk
from sqlalchemy import and_, select, text
from sqlalchemy.dialects.postgresql import insert

from database import AsyncSessionLocal, ExpertiseEvidence, Skill, User
from processors.classifier import SkillEvaluation


class StorageService:
    def __init__(self):
        pass

    async def is_database_empty(self) -> bool:
        """Check if database is empty (no expertise evidence exists)"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ExpertiseEvidence).limit(1))
            return result.scalar_one_or_none() is None

    async def upsert_users(self, users_data: dict[str, dict[str, Any]]):
        """Insert or update users from Slack data"""
        async with AsyncSessionLocal() as session:
            for slack_id, user_data in users_data.items():
                # Check if user exists
                result = await session.execute(
                    select(User).where(User.slack_id == slack_id)
                )
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    # Update existing user
                    existing_user.display_name = user_data["display_name"]
                    existing_user.timezone = user_data.get("timezone")
                else:
                    # Create new user
                    new_user = User(
                        slack_id=slack_id,
                        display_name=user_data["display_name"],
                        timezone=user_data.get("timezone"),
                    )
                    session.add(new_user)

            await session.commit()

    async def get_user_by_slack_id(self, slack_id: str) -> User | None:
        """Get user by Slack ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.slack_id == slack_id)
            )
            return result.scalar_one_or_none()

    async def get_skill_by_key(self, skill_key: str) -> Skill | None:
        """Get skill by skill_key"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Skill).where(Skill.skill_key == skill_key)
            )
            return result.scalar_one_or_none()

    async def get_all_skills(self) -> list[Skill]:
        """Get all skills from database"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Skill))
            return list(result.scalars().all())

    async def upsert_skills(self, skills_data: list[dict[str, Any]]):
        """Insert or update skills from JSON files"""
        async with AsyncSessionLocal() as session:
            for skill_data in skills_data:
                stmt = insert(Skill).values(
                    skill_key=skill_data["skill_key"],
                    name=skill_data["name"],
                    domain=skill_data["domain"],
                    aliases=skill_data.get("aliases"),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["skill_key"],
                    set_=dict(
                        name=stmt.excluded.name,
                        domain=stmt.excluded.domain,
                        aliases=stmt.excluded.aliases,
                    ),
                )
                await session.execute(stmt)

            await session.commit()

    @sentry_sdk.trace
    async def store_expertise_evidence(
        self,
        user_slack_id: str,
        skill_keys: list[str],
        evaluations: list[SkillEvaluation],
        evidence_date: date,
        message_hash: str | None = None,
    ):
        """Store expertise evidence in database"""
        async with AsyncSessionLocal() as session:
            # Get user
            user = await self.get_user_by_slack_id(user_slack_id)
            if not user:
                # User should exist, but skip if not found
                return

            # Store each evaluation
            for evaluation in evaluations:
                # Get skill
                skill = await self.get_skill_by_key(evaluation.skill_key)
                if not skill:
                    # Skill should exist, but skip if not found
                    continue

                # Check for existing evidence with same hash to avoid duplicates
                if message_hash:
                    existing = await session.execute(
                        select(ExpertiseEvidence).where(
                            and_(
                                ExpertiseEvidence.user_id == user.user_id,
                                ExpertiseEvidence.skill_id == skill.skill_id,
                                ExpertiseEvidence.message_hash == message_hash,
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Skip duplicate

                # Create new evidence
                evidence = ExpertiseEvidence(
                    user_id=user.user_id,
                    skill_id=skill.skill_id,
                    label=evaluation.label,
                    confidence=evaluation.confidence,
                    evidence_date=evidence_date,
                    message_hash=message_hash,
                )
                session.add(evidence)

            await session.commit()

    @sentry_sdk.trace
    async def get_experts_for_skill(
        self, skill_key: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get experts for a skill using query-time decay calculation"""
        async with AsyncSessionLocal() as session:
            # This would implement the query-time decay calculation
            # For now, return a simple query
            # Simplified query without time decay for now (can add back later)
            query = """
            SELECT
                u.display_name,
                u.slack_id,
                s.name as skill_name,
                AVG(
                    CASE
                        WHEN ee.label = 'positive_expertise' THEN ee.confidence
                        WHEN ee.label = 'negative_expertise' THEN -ee.confidence * 0.5
                        ELSE 0
                    END
                ) as expertise_score,
                COUNT(*) as evidence_count
            FROM expertise_evidence ee
            JOIN users u ON ee.user_id = u.user_id
            JOIN skills s ON ee.skill_id = s.skill_id
            WHERE s.skill_key = :skill_key
              AND ee.evidence_date >= CURRENT_DATE - INTERVAL '180 days'
            GROUP BY u.user_id, u.display_name, u.slack_id, s.name
            HAVING AVG(
                CASE
                    WHEN ee.label = 'positive_expertise' THEN ee.confidence
                    WHEN ee.label = 'negative_expertise' THEN -ee.confidence * 0.5
                    ELSE 0
                END
            ) > 0.1
            ORDER BY expertise_score DESC
            LIMIT :limit
            """

            result = await session.execute(
                text(query), {"skill_key": skill_key, "limit": limit}
            )

            experts = []
            for row in result:
                experts.append(
                    {
                        "display_name": row.display_name,
                        "slack_id": row.slack_id,
                        "skill_name": row.skill_name,
                        "expertise_score": float(row.expertise_score),
                        "evidence_count": row.evidence_count,
                    }
                )

            return experts
