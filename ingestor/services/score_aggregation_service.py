"""Service for aggregating expertise evidence into user skill scores"""

import logging
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select, text

from database import AsyncSessionLocal, ExpertiseEvidence, UserSkillScore

logger = logging.getLogger(__name__)


class ScoreAggregationService:
    """Service to aggregate expertise evidence into user skill scores"""

    def __init__(self):
        pass

    async def aggregate_all_scores(self) -> dict[str, Any]:
        """Recalculate all user skill scores from expertise evidence"""
        logger.info("Starting full score aggregation...")

        async with AsyncSessionLocal() as session:
            # Clear existing scores
            await session.execute(delete(UserSkillScore))
            logger.info("Cleared existing user skill scores")

            # Aggregate scores by user and skill
            query = text("""
            SELECT
                ee.user_id,
                ee.skill_id,
                AVG(
                    CASE
                        WHEN ee.label = 'positive_expertise' THEN ee.confidence
                        WHEN ee.label = 'negative_expertise' THEN -ee.confidence * 0.5
                        ELSE 0
                    END
                ) as avg_score,
                COUNT(*) as evidence_count,
                MAX(ee.evidence_date) as last_evidence_date
            FROM expertise_evidence ee
            WHERE ee.evidence_date >= CURRENT_DATE - INTERVAL '180 days'
            GROUP BY ee.user_id, ee.skill_id
            HAVING AVG(
                CASE
                    WHEN ee.label = 'positive_expertise' THEN ee.confidence
                    WHEN ee.label = 'negative_expertise' THEN -ee.confidence * 0.5
                    ELSE 0
                END
            ) > 0.1
            """)

            result = await session.execute(query)
            aggregated_data = result.fetchall()

            # Insert new scores
            score_count = 0
            for row in aggregated_data:
                user_skill_score = UserSkillScore(
                    user_id=row.user_id,
                    skill_id=row.skill_id,
                    score=float(row.avg_score),
                    evidence_count=int(row.evidence_count),
                    last_evidence_date=row.last_evidence_date,
                )
                session.add(user_skill_score)
                score_count += 1

            await session.commit()

            logger.info(f"Aggregated {score_count} user skill scores")

            return {
                "aggregated_scores": score_count,
                "evidence_processed": len(aggregated_data),
                "status": "completed",
            }

    async def update_user_skill_score(
        self,
        user_id: int,
        skill_id: int,
        new_evidence_label: str,
        new_evidence_confidence: float,
        evidence_date: date,
    ):
        """Incrementally update a user's skill score when new evidence arrives"""

        async with AsyncSessionLocal() as session:
            # Calculate evidence value
            evidence_value = self._calculate_evidence_value(
                new_evidence_label, new_evidence_confidence
            )

            # Get current score or create new record
            existing_score = await session.execute(
                select(UserSkillScore).where(
                    UserSkillScore.user_id == user_id,
                    UserSkillScore.skill_id == skill_id,
                )
            )
            current = existing_score.scalar_one_or_none()

            if current:
                # Update existing record using exponential moving average
                alpha = 0.1  # Learning rate
                new_score = (1 - alpha) * current.score + alpha * evidence_value

                current.score = new_score
                current.evidence_count += 1
                current.last_evidence_date = max(
                    current.last_evidence_date, evidence_date
                )
            else:
                # Create new record
                new_score_record = UserSkillScore(
                    user_id=user_id,
                    skill_id=skill_id,
                    score=evidence_value,
                    evidence_count=1,
                    last_evidence_date=evidence_date,
                )
                session.add(new_score_record)

            await session.commit()
            logger.debug(f"Updated skill score for user {user_id}, skill {skill_id}")

    def _calculate_evidence_value(self, label: str, confidence: float) -> float:
        """Convert evidence label and confidence to a score value"""
        if label == "positive_expertise":
            return confidence
        elif label == "negative_expertise":
            return -confidence * 0.5
        else:  # neutral
            return 0.0

    async def get_aggregation_stats(self) -> dict[str, Any]:
        """Get statistics about current score aggregation"""
        async with AsyncSessionLocal() as session:
            # Count evidence records
            evidence_result = await session.execute(
                select(func.count(ExpertiseEvidence.evidence_id))
            )
            evidence_count = evidence_result.scalar()

            # Count user skill scores
            scores_result = await session.execute(
                select(func.count(UserSkillScore.user_id))
            )
            scores_count = scores_result.scalar()

            # Get users with scores
            users_with_scores_result = await session.execute(
                select(func.count(func.distinct(UserSkillScore.user_id)))
            )
            users_with_scores = users_with_scores_result.scalar()

            return {
                "total_evidence": evidence_count,
                "total_scores": scores_count,
                "users_with_scores": users_with_scores,
                "aggregation_ratio": scores_count / evidence_count
                if evidence_count > 0
                else 0,
            }


# Global service instance
_aggregation_service: ScoreAggregationService | None = None


def get_aggregation_service() -> ScoreAggregationService:
    """Get the global aggregation service instance"""
    global _aggregation_service
    if _aggregation_service is None:
        _aggregation_service = ScoreAggregationService()
    return _aggregation_service
