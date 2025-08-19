"""Natural language query parsing for skill extraction"""

import logging
import re

from models.slack_models import ExpertQuery, ParsedSlackMessage

logger = logging.getLogger(__name__)


class QueryParser:
    """Extracts skills and intent from natural language queries"""

    def __init__(self):
        # Common programming languages and technologies
        self.tech_skills = {
            # Programming languages
            "python",
            "javascript",
            "typescript",
            "java",
            "c++",
            "c#",
            "go",
            "rust",
            "ruby",
            "php",
            "swift",
            "kotlin",
            "scala",
            "clojure",
            "haskell",
            "erlang",
            "r",
            "matlab",
            "perl",
            "lua",
            "dart",
            "elixir",
            "f#",
            "ocaml",
            # Web technologies
            "react",
            "vue",
            "angular",
            "nodejs",
            "express",
            "nextjs",
            "nuxt",
            "django",
            "flask",
            "fastapi",
            "spring",
            "laravel",
            "rails",
            "html",
            "css",
            "sass",
            "scss",
            "tailwind",
            "bootstrap",
            # Databases
            "postgresql",
            "postgres",
            "mysql",
            "mongodb",
            "redis",
            "sqlite",
            "oracle",
            "cassandra",
            "dynamodb",
            "elasticsearch",
            "neo4j",
            # Cloud & DevOps
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "terraform",
            "ansible",
            "jenkins",
            "gitlab",
            "github",
            "git",
            "svn",
            "linux",
            "ubuntu",
            "centos",
            "debian",
            "macos",
            "windows",
            # Data & ML
            "pandas",
            "numpy",
            "pytorch",
            "tensorflow",
            "scikit-learn",
            "jupyter",
            "spark",
            "hadoop",
            "kafka",
            "airflow",
            "tableau",
            "powerbi",
            "looker",
            "grafana",
            # Mobile
            "ios",
            "android",
            "flutter",
            "react-native",
            "xamarin",
            # Testing
            "pytest",
            "jest",
            "cypress",
            "selenium",
            "junit",
            "rspec",
            # Other tools
            "vim",
            "emacs",
            "vscode",
            "intellij",
            "sublime",
            "atom",
            "slack",
            "jira",
            "confluence",
            "notion",
            "figma",
            "sketch",
        }

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

    def parse_query(self, message: ParsedSlackMessage) -> ExpertQuery | None:
        """Parse a message and extract an expert search query"""
        try:
            text = message.cleaned_text

            # Try to match against known patterns
            for pattern, query_type in self.compiled_patterns:
                match = pattern.search(text)
                if match:
                    skill_text = match.group(1).strip()
                    skills = self._extract_skills_from_text(skill_text)

                    if skills:
                        confidence = self._calculate_confidence(
                            text, skills, query_type
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
                            f"Extracted query: {query_type} for skills {skills} (confidence: {confidence:.2f})"
                        )
                        return query

            # Fallback: try to extract any tech skills mentioned
            fallback_skills = self._extract_skills_from_text(text)
            if fallback_skills:
                query = ExpertQuery(
                    original_text=message.text,
                    skills=fallback_skills,
                    query_type="general_mention",
                    confidence=0.3,  # Lower confidence for fallback
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

    def _extract_skills_from_text(self, text: str) -> list[str]:
        """Extract technology skills from text"""
        text_lower = text.lower()

        # Remove common words that might interfere
        words_to_remove = ["and", "or", "with", "in", "on", "at", "the", "a", "an"]

        # Split text into potential skill tokens
        # Handle both spaces and common separators
        tokens = re.split(r"[,\s/&+\-]+", text_lower)
        tokens = [token.strip() for token in tokens if token.strip()]

        # Find exact matches
        found_skills = []
        for token in tokens:
            if token in self.tech_skills and token not in words_to_remove:
                found_skills.append(token)

        # Look for compound skills (e.g., "machine learning", "data science")
        compound_skills = self._find_compound_skills(text_lower)
        found_skills.extend(compound_skills)

        # Remove duplicates while preserving order
        unique_skills = []
        for skill in found_skills:
            if skill not in unique_skills:
                unique_skills.append(skill)

        return unique_skills

    def _find_compound_skills(self, text: str) -> list[str]:
        """Find compound/multi-word skills"""
        compound_skills = [
            "machine learning",
            "deep learning",
            "data science",
            "data analysis",
            "web development",
            "mobile development",
            "game development",
            "software engineering",
            "devops",
            "site reliability",
            "quality assurance",
            "product management",
            "project management",
            "user experience",
            "user interface",
            "computer vision",
            "natural language processing",
            "artificial intelligence",
            "cloud computing",
            "distributed systems",
            "microservices",
            "database design",
            "system architecture",
            "api design",
            "frontend development",
            "backend development",
            "full stack",
            "react native",
            "node js",
            "express js",
            "next js",
            "spring boot",
            "ruby on rails",
            "asp net",
        ]

        found = []
        for skill in compound_skills:
            if skill in text:
                found.append(skill)

        return found

    def _calculate_confidence(
        self, text: str, skills: list[str], query_type: str
    ) -> float:
        """Calculate confidence score for the parsed query"""
        base_confidence = 0.7

        # Boost confidence for specific query types
        high_confidence_types = ["who_knows", "expert_in", "find_expert"]
        if query_type in high_confidence_types:
            base_confidence = 0.9

        # Boost confidence if multiple skills found
        if len(skills) > 1:
            base_confidence += 0.1

        # Boost confidence for exact tech skill matches
        exact_matches = sum(1 for skill in skills if skill in self.tech_skills)
        if exact_matches > 0:
            base_confidence += 0.1 * (exact_matches / len(skills))

        # Reduce confidence for very long skill lists (might be noise)
        if len(skills) > 3:
            base_confidence -= 0.1

        # Boost confidence if question mark present
        if "?" in text:
            base_confidence += 0.05

        return min(1.0, base_confidence)

    def get_supported_skills(self) -> list[str]:
        """Get list of supported skills for validation"""
        return sorted(list(self.tech_skills))
