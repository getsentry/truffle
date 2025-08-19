import json

from services.storage_service import StorageService
from taxonomy import Skill, SkillMatcher


class SkillService:
    def __init__(self):
        self.matcher = None
        self._skills_cache = None

    async def _load_skills_from_db(self) -> list[Skill]:
        """Load skills from database and convert to Skill objects"""
        if self._skills_cache is not None:
            return self._skills_cache

        storage = StorageService()
        db_skills = await storage.get_all_skills()

        skills = []
        for db_skill in db_skills:
            # Parse aliases from JSON string
            aliases = []
            if db_skill.aliases:
                try:
                    aliases = json.loads(db_skill.aliases)
                except (json.JSONDecodeError, TypeError):
                    aliases = []

            skills.append(
                Skill(
                    key=db_skill.skill_key,
                    name=db_skill.name,
                    domain=db_skill.domain,
                    aliases=tuple(aliases),
                )
            )

        self._skills_cache = skills
        return skills

    async def match_text(self, text: str) -> list[str]:
        """Extract skill keys from text using database taxonomy"""
        if not text:
            return []

        if self.matcher is None:
            skills = await self._load_skills_from_db()
            self.matcher = SkillMatcher(skills)

        return self.matcher.match_text(text)

    async def get_skill_info(self, skill_key: str):
        """Get skill information from matcher"""
        if self.matcher is None:
            skills = await self._load_skills_from_db()
            self.matcher = SkillMatcher(skills)

        return self.matcher.describe(skill_key)

    async def reload_skills(self):
        """Force reload skills from database (clear cache)"""
        self._skills_cache = None
        self.matcher = None
