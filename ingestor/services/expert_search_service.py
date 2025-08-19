import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import aliased

from database import AsyncSessionLocal, ExpertiseEvidence, Skill, User

logger = logging.getLogger(__name__)


class SortBy(Enum):
    SCORE = "score"
    RECENT = "recent"
    EVIDENCE_COUNT = "evidence_count"
    ALPHABETICAL = "alphabetical"


@dataclass
class ExpertQuery:
    """Configuration for expert search queries"""
    # Core search parameters
    skill_query: str = ""
    skill_keys: list[str] = field(default_factory=list)

    # Filtering parameters
    min_confidence: float = 0.1
    min_evidence_count: int = 1
    time_window_days: int = 180
    include_negative: bool = False
    exclude_neutral: bool = True

    # Sorting and pagination
    sort_by: SortBy = SortBy.SCORE
    limit: int = 10
    offset: int = 0

    # Score calculation parameters
    time_decay_factor: float = 0.95  # Daily decay factor
    negative_weight: float = 0.5     # How much to penalize negative signals

    def __post_init__(self):
        if isinstance(self.sort_by, str):
            self.sort_by = SortBy(self.sort_by)


@dataclass
class ExpertResult:
    """Result of an expert search"""
    # User information
    slack_id: str
    display_name: str
    timezone: str | None

    # Expertise information
    skill_name: str
    skill_key: str
    expertise_score: float
    confidence_level: str  # high, medium, low
    evidence_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    last_activity_date: date | None

    # Metadata
    trend: str | None = None  # increasing, stable, decreasing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "user": {
                "slack_id": self.slack_id,
                "display_name": self.display_name,
                "timezone": self.timezone
            },
            "expertise": {
                "skill_name": self.skill_name,
                "skill_key": self.skill_key,
                "score": round(self.expertise_score, 3),
                "confidence_level": self.confidence_level,
                "evidence_count": self.evidence_count,
                "last_activity": self.last_activity_date.isoformat() if self.last_activity_date else None,
                "trend": self.trend
            },
            "evidence_summary": {
                "positive_signals": self.positive_count,
                "negative_signals": self.negative_count,
                "neutral_signals": self.neutral_count
            }
        }


class ExpertSearchService:
    """Advanced expert search with flexible query methods and scoring"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def search_experts_by_skill_key(self, skill_key: str, query: ExpertQuery | None = None) -> list[ExpertResult]:
        """Search experts by exact skill key (most efficient)"""
        if query is None:
            query = ExpertQuery()
        query.skill_keys = [skill_key]
        return await self._execute_expert_query(query)

    async def search_experts_by_skill_name(self, skill_name: str, query: ExpertQuery | None = None) -> list[ExpertResult]:
        """Search experts by skill name (user-friendly)"""
        if query is None:
            query = ExpertQuery()

        # Find skills matching the name
        skill_keys = await self._find_skills_by_name(skill_name)
        if not skill_keys:
            self.logger.warning(f"No skills found matching name: {skill_name}")
            return []

        query.skill_keys = skill_keys
        return await self._execute_expert_query(query)

    async def search_experts_fuzzy(self, skill_query: str, query: ExpertQuery | None = None) -> list[ExpertResult]:
        """Search experts with fuzzy/partial matching"""
        if query is None:
            query = ExpertQuery()

        # Find skills using fuzzy matching
        skill_keys = await self._find_skills_fuzzy(skill_query)
        if not skill_keys:
            self.logger.warning(f"No skills found matching fuzzy query: {skill_query}")
            return []

        query.skill_keys = skill_keys
        return await self._execute_expert_query(query)

    async def search_experts_by_aliases(self, aliases: list[str], query: ExpertQuery | None = None) -> list[ExpertResult]:
        """Search experts by skill aliases"""
        if query is None:
            query = ExpertQuery()

        skill_keys = await self._find_skills_by_aliases(aliases)
        if not skill_keys:
            self.logger.warning(f"No skills found matching aliases: {aliases}")
            return []

        query.skill_keys = skill_keys
        return await self._execute_expert_query(query)

    async def _find_skills_by_name(self, name: str) -> list[str]:
        """Find skill keys by skill name (case insensitive)"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Skill.skill_key).where(
                    func.lower(Skill.name) == func.lower(name)
                )
            )
            return [row.skill_key for row in result]

    async def _find_skills_fuzzy(self, query: str) -> list[str]:
        """Find skill keys using fuzzy/partial matching"""
        async with AsyncSessionLocal() as session:
            # Use PostgreSQL ILIKE for partial matching
            search_pattern = f"%{query.lower()}%"
            result = await session.execute(
                select(Skill.skill_key, Skill.name).where(
                    or_(
                        func.lower(Skill.name).like(search_pattern),
                        func.lower(Skill.skill_key).like(search_pattern),
                        func.lower(Skill.aliases).like(search_pattern)
                    )
                )
            )
            skills = [(row.skill_key, row.name) for row in result]

            # Log matches for debugging
            if skills:
                skill_names = [skill[1] for skill in skills]
                self.logger.debug(f"Fuzzy search '{query}' matched: {skill_names}")

            return [skill[0] for skill in skills]

    async def _find_skills_by_aliases(self, aliases: list[str]) -> list[str]:
        """Find skill keys by aliases (stored as JSON in aliases column)"""
        async with AsyncSessionLocal() as session:
            conditions = []
            for alias in aliases:
                # Search in JSON aliases column
                conditions.append(
                    func.lower(Skill.aliases).like(f"%{alias.lower()}%")
                )

            result = await session.execute(
                select(Skill.skill_key).where(or_(*conditions))
            )
            return [row.skill_key for row in result]

    async def _execute_expert_query(self, query: ExpertQuery) -> list[ExpertResult]:
        """Execute the main expert query with advanced scoring and filtering"""
        if not query.skill_keys:
            return []

        async with AsyncSessionLocal() as session:
            # Build the main query with time decay and advanced scoring
            sql_query = self._build_expert_sql_query(query)

            result = await session.execute(
                text(sql_query),
                {
                    "skill_keys": query.skill_keys,
                    "min_confidence": query.min_confidence,
                    "min_evidence_count": query.min_evidence_count,
                    "time_window_days": query.time_window_days,
                    "time_decay_factor": query.time_decay_factor,
                    "negative_weight": query.negative_weight,
                    "limit": query.limit,
                    "offset": query.offset
                }
            )

            experts = []
            for row in result:
                expert = ExpertResult(
                    slack_id=row.slack_id,
                    display_name=row.display_name,
                    timezone=row.timezone,
                    skill_name=row.skill_name,
                    skill_key=row.skill_key,
                    expertise_score=float(row.expertise_score),
                    confidence_level=self._get_confidence_level(float(row.expertise_score)),
                    evidence_count=row.evidence_count,
                    positive_count=row.positive_count,
                    negative_count=row.negative_count,
                    neutral_count=row.neutral_count,
                    last_activity_date=row.last_activity_date
                )
                experts.append(expert)

            return experts

    def _build_expert_sql_query(self, query: ExpertQuery) -> str:
        """Build SQL query with advanced scoring and time decay"""

        # Build WHERE conditions
        where_conditions = ["s.skill_key = ANY(:skill_keys)"]

        if query.time_window_days > 0:
            where_conditions.append("ee.evidence_date >= CURRENT_DATE - :time_window_days * INTERVAL '1 day'")

        if query.exclude_neutral:
            where_conditions.append("ee.label != 'neutral'")

        if not query.include_negative:
            where_conditions.append("ee.label != 'negative_expertise'")

        where_clause = " AND ".join(where_conditions)

        # Build ORDER BY clause
        if query.sort_by == SortBy.SCORE:
            order_by = "expertise_score DESC"
        elif query.sort_by == SortBy.RECENT:
            order_by = "last_activity_date DESC NULLS LAST"
        elif query.sort_by == SortBy.EVIDENCE_COUNT:
            order_by = "evidence_count DESC"
        else:  # ALPHABETICAL
            order_by = "u.display_name ASC"

        return f"""
            SELECT
                u.slack_id,
                u.display_name,
                u.timezone,
                s.name as skill_name,
                s.skill_key,
                AVG(
                    CASE
                        WHEN ee.label = 'positive_expertise' THEN
                            ee.confidence * POWER(:time_decay_factor, (CURRENT_DATE - ee.evidence_date))
                        WHEN ee.label = 'negative_expertise' THEN
                            -ee.confidence * :negative_weight * POWER(:time_decay_factor, (CURRENT_DATE - ee.evidence_date))
                        ELSE 0
                    END
                ) as expertise_score,
                COUNT(*) as evidence_count,
                COUNT(*) FILTER (WHERE ee.label = 'positive_expertise') as positive_count,
                COUNT(*) FILTER (WHERE ee.label = 'negative_expertise') as negative_count,
                COUNT(*) FILTER (WHERE ee.label = 'neutral') as neutral_count,
                MAX(ee.evidence_date) as last_activity_date
            FROM expertise_evidence ee
            JOIN users u ON ee.user_id = u.user_id
            JOIN skills s ON ee.skill_id = s.skill_id
            WHERE {where_clause}
            GROUP BY u.user_id, u.slack_id, u.display_name, u.timezone, s.skill_id, s.name, s.skill_key
            HAVING
                COUNT(*) >= :min_evidence_count
                AND AVG(
                    CASE
                        WHEN ee.label = 'positive_expertise' THEN
                            ee.confidence * POWER(:time_decay_factor, (CURRENT_DATE - ee.evidence_date))
                        WHEN ee.label = 'negative_expertise' THEN
                            -ee.confidence * :negative_weight * POWER(:time_decay_factor, (CURRENT_DATE - ee.evidence_date))
                        ELSE 0
                    END
                ) >= :min_confidence
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """

    def _get_confidence_level(self, score: float) -> str:
        """Convert numeric score to confidence level"""
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"

    async def get_skill_suggestions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get skill suggestions for autocomplete"""
        async with AsyncSessionLocal() as session:
            search_pattern = f"%{query.lower()}%"
            result = await session.execute(
                select(Skill.skill_key, Skill.name, Skill.domain, Skill.aliases).where(
                    or_(
                        func.lower(Skill.name).like(search_pattern),
                        func.lower(Skill.skill_key).like(search_pattern)
                    )
                ).limit(limit)
            )

            suggestions = []
            for row in result:
                aliases = []
                if row.aliases:
                    try:
                        aliases = json.loads(row.aliases)
                    except (json.JSONDecodeError, TypeError):
                        aliases = []

                suggestions.append({
                    "skill_key": row.skill_key,
                    "name": row.name,
                    "domain": row.domain,
                    "aliases": aliases
                })

            return suggestions
