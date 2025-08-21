"""Natural language query parsing for skill extraction"""

import logging
import re
from typing import TYPE_CHECKING

import sentry_sdk

from models.slack_models import ExpertQuery, ParsedSlackMessage

if TYPE_CHECKING:
    from .skill_cache_service import SkillCacheService

logger = logging.getLogger(__name__)


class QueryParser:
    """Extracts skills and intent from natural language queries"""

    def __init__(self, skill_cache_service: "SkillCacheService"):
        self.skill_cache_service = skill_cache_service

        # Skills are now loaded dynamically from database via skill_cache_service

        # Query patterns for different types of expert searches
        self.query_patterns = [
            # "Who knows X?" patterns
            (r"who knows?\s+(?:about\s+)?(.+?)(?:\?|$)", "who_knows"),
            (
                r"who is\s+(?:an?\s+)?expert\s+(?:in|on|with|at)\s+(.+?)(?:\?|$)",
                "expert_in",
            ),
            (r"who can help\s+(?:me\s+)?(?:with\s+)?(.+?)(?:\?|$)", "help_with"),
            (r"who has experience\s+(?:with\s+)?(.+?)(?:\?|$)", "experience_with"),
            (
                r"find\s+(?:me\s+)?(?:an?\s+)?expert\s+(?:in|on|with|for)\s+(.+?)(?:\?|$)",
                "find_expert",
            ),
            (
                r"need\s+(?:an?\s+)?expert\s+(?:in|on|with|for)\s+(.+?)(?:\?|$)",
                "need_expert",
            ),
            (
                r"looking for\s+(?:an?\s+)?expert\s+(?:in|on|with)\s+(.+?)(?:\?|$)",
                "looking_for",
            ),
            (r"anyone know\s+(?:about\s+)?(.+?)(?:\?|$)", "anyone_know"),
            (r"who should I ask about\s+(.+?)(?:\?|$)", "who_ask"),
            (
                r"who's\s+(?:the\s+)?(?:best|good)\s+(?:at|with)\s+(.+?)(?:\?|$)",
                "best_at",
            ),
            # "I need help with X" patterns
            (r"(?:I\s+)?need help\s+(?:with\s+)?(.+?)(?:\?|$)", "need_help"),
            (
                r"(?:can\s+)?(?:someone\s+)?help\s+(?:me\s+)?(?:with\s+)?(.+?)(?:\?|$)",
                "help_request",
            ),
            (r"advice\s+(?:on\s+)?(.+?)(?:\?|$)", "advice_on"),
            (r"guidance\s+(?:on\s+)?(.+?)(?:\?|$)", "guidance_on"),
        ]

        # Compile regex patterns
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), query_type)
            for pattern, query_type in self.query_patterns
        ]

    @sentry_sdk.trace
    async def parse_query(self, message: ParsedSlackMessage) -> ExpertQuery | None:
        """Parse a message and extract an expert search query"""
        try:
            text = message.cleaned_text
            logger.debug(f"QueryParser.parse_query called with text: '{text}'")

            # Try to match against known patterns
            for pattern, query_type in self.compiled_patterns:
                match = pattern.search(text)
                if match:
                    skill_text = match.group(1).strip()
                    logger.debug(
                        f"Pattern '{query_type}' matched! Extracted skill_text: '{skill_text}'"
                    )
                    (
                        skills,
                        is_partial,
                    ) = await self._extract_skills_from_text_with_match_type(skill_text)

                    if skills:
                        confidence = self._calculate_confidence(
                            text, skills, query_type, is_partial
                        )

                        query = ExpertQuery(
                            original_text=message.text,
                            skills=skills,
                            query_type=query_type,
                            confidence=confidence,
                            user_id=message.user_id,
                            channel_id=message.channel_id,
                            thread_ts=message.thread_ts,
                        )

                        logger.info(
                            f"Extracted query: {query_type} for skills {skills} "
                            f"(confidence: {confidence:.2f})"
                        )
                        return query

            # Fallback: try to extract any tech skills mentioned
            logger.debug(
                f"No pattern matched, trying fallback skill extraction on: '{text}'"
            )
            (
                fallback_skills,
                is_partial,
            ) = await self._extract_skills_from_text_with_match_type(text)

            if fallback_skills:
                fallback_confidence = (
                    0.3 if not is_partial else 0.2
                )  # Even lower confidence for partial fallback
                query = ExpertQuery(
                    original_text=message.text,
                    skills=fallback_skills,
                    query_type="general_mention",
                    confidence=fallback_confidence,
                    user_id=message.user_id,
                    channel_id=message.channel_id,
                    thread_ts=message.thread_ts,
                )

                logger.info(f"Fallback query for skills {fallback_skills}")
                return query

            logger.info(f"No skills found in message: {text}")
            return None

        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            return None

    @sentry_sdk.trace
    async def _extract_skills_from_text_with_match_type(
        self, text: str
    ) -> tuple[list[str], bool]:
        """Extract technology skills from text, returning skills and whether partial matching was used"""
        skills = await self._extract_skills_from_text(text)
        # For now, track this in the logs - more sophisticated tracking could be added later
        is_partial = (
            "partial" in str(self._last_extraction_method)
            if hasattr(self, "_last_extraction_method")
            else False
        )
        return skills, is_partial

    @sentry_sdk.trace
    async def _extract_skills_from_text(self, text: str) -> list[str]:
        """Extract technology skills from text using database skills"""
        text_lower = text.lower()

        # Remove common words that might interfere
        words_to_remove = {"and", "or", "with", "in", "on", "at", "the", "a", "an"}

        # Get all skill terms from database (names + aliases)
        all_skill_terms = await self.skill_cache_service.get_all_skill_terms()
        logger.debug(f"Available skill terms count: {len(all_skill_terms)}")

        # Split text into potential skill tokens
        # Handle both spaces and common separators
        tokens = re.split(r"[,\s/&+\-]+", text_lower)
        tokens = [token.strip() for token in tokens if token.strip()]

        # Find exact matches against database skills
        found_skills = []
        for token in tokens:
            logger.debug(
                f"Checking token: '{token}' (in skill_terms: {token in all_skill_terms}, is_common_word: {token in words_to_remove})"
            )
            if token in all_skill_terms and token not in words_to_remove:
                # Get the actual skill info to return the canonical name
                skill_info = await self.skill_cache_service.get_skill_by_term(token)
                if skill_info and skill_info.key not in found_skills:
                    logger.debug(f"Found skill: {skill_info.key} for token: {token}")
                    found_skills.append(skill_info.key)

        # Look for compound/multi-word skills from database
        compound_skills = await self._find_compound_skills(text_lower)
        found_skills.extend(compound_skills)

        # If no exact matches found, try partial matching for multi-word skills
        if not found_skills:
            partial_skills = await self._find_partial_matches(tokens, all_skill_terms)
            found_skills.extend(partial_skills)
            if partial_skills:
                self._last_extraction_method = "partial_matching"
            logger.debug(f"Partial matching found: {partial_skills}")
        else:
            self._last_extraction_method = "exact_matching"

        # Remove duplicates while preserving order
        unique_skills = []
        for skill in found_skills:
            if skill not in unique_skills:
                unique_skills.append(skill)

        logger.debug(f"Final unique skills: {unique_skills}")
        return unique_skills

    @sentry_sdk.trace
    async def _find_compound_skills(self, text: str) -> list[str]:
        """Find compound/multi-word skills from database"""
        found = []

        # Get all skills from database
        all_skill_terms = await self.skill_cache_service.get_all_skill_terms()

        # Look for multi-word skills (containing spaces)
        multi_word_skills = [term for term in all_skill_terms if " " in term]

        for skill_term in multi_word_skills:
            if skill_term in text:
                # Get the actual skill info to return the canonical key
                skill_info = await self.skill_cache_service.get_skill_by_term(
                    skill_term
                )
                if skill_info and skill_info.key not in found:
                    found.append(skill_info.key)

        return found

    @sentry_sdk.trace
    async def _find_partial_matches(
        self, tokens: list[str], all_skill_terms: set[str]
    ) -> list[str]:
        """Find skills where user tokens partially match multi-word skill names/aliases"""
        found = []
        words_to_remove = {
            "and",
            "or",
            "with",
            "in",
            "on",
            "at",
            "the",
            "a",
            "an",
            "stuff",
            "things",
        }

        # Filter tokens to exclude common words
        meaningful_tokens = [
            token for token in tokens if token not in words_to_remove and len(token) > 2
        ]

        logger.debug(f"Meaningful tokens for partial matching: {meaningful_tokens}")

        # Check each meaningful token against all skill terms
        for token in meaningful_tokens:
            # Find skill terms that contain this token
            matching_terms = [term for term in all_skill_terms if token in term]
            logger.debug(
                f"Token '{token}' matches terms: {matching_terms[:5]}..."
            )  # Log first 5

            for term in matching_terms:
                skill_info = await self.skill_cache_service.get_skill_by_term(term)
                if skill_info and skill_info.key not in found:
                    logger.debug(
                        f"Partial match: '{token}' -> '{term}' -> skill '{skill_info.key}'"
                    )
                    found.append(skill_info.key)

        return found

    @sentry_sdk.trace
    def _calculate_confidence(
        self,
        text: str,
        skills: list[str],
        query_type: str,
        is_partial_match: bool = False,
    ) -> float:
        """Calculate confidence score for the parsed query"""
        base_confidence = 0.7

        # Reduce confidence for partial matches
        if is_partial_match:
            base_confidence = 0.5

        # Boost confidence for specific query types
        high_confidence_types = ["who_knows", "expert_in", "find_expert"]
        if query_type in high_confidence_types:
            base_confidence = 0.9 if not is_partial_match else 0.7

        # Boost confidence if multiple skills found
        if len(skills) > 1:
            base_confidence += 0.1

        # Boost confidence for skills found in database
        # Note: All skills are now from database, so all matches are valid
        if len(skills) > 0:
            base_confidence += 0.1

        # Reduce confidence for very long skill lists (might be noise)
        if len(skills) > 3:
            base_confidence -= 0.1

        # Boost confidence if question mark present
        if "?" in text:
            base_confidence += 0.05

        return min(1.0, base_confidence)

    @sentry_sdk.trace
    async def get_supported_skills(self) -> list[str]:
        """Get list of supported skills for validation"""
        skills = await self.skill_cache_service.get_skills()
        return [skill.key for skill in skills]
