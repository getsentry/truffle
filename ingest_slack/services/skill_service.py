from taxonomy import SkillMatcher


class SkillService:
    def __init__(self):
        self.matcher = SkillMatcher()

    def match_text(self, text: str) -> list[str]:
        """Extract skill keys from text using the taxonomy matcher"""
        if not text or not self.matcher:
            return []

        return self.matcher.match_text(text)

    def get_skill_info(self, skill_key: str):
        """Get skill information from taxonomy"""
        if not self.matcher:
            return None

        return self.matcher.describe(skill_key)

    def get_all_skills(self):
        """Get all available skills from taxonomy"""
        if not self.matcher:
            return []

        # This would need to be implemented in the SkillMatcher class
        # For now, we'll return empty list
        return []
