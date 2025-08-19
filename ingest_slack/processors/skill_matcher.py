from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    domain: str
    aliases: tuple[str, ...]


class SkillMatcher:
    """Very lightweight alias-based matcher.

    - Word-boundary, case-insensitive matching over text
    - Maps any alias to a canonical skill key
    """

    def __init__(self, skills: Iterable[Skill]) -> None:
        self.skills: list[Skill] = list(skills)
        self.alias_to_key: dict[str, str] = {}
        self.key_to_skill: dict[str, Skill] = {s.key: s for s in self.skills}
        for skill in self.skills:
            for alias in (skill.name.lower(),) + skill.aliases:
                self.alias_to_key[alias] = skill.key

        # Precompile regexes per alias
        # Use negative lookbehind/ahead to avoid partial matches inside words
        boundary = r"(?<![\w/#.])({})(?![\w-])"
        self.alias_regex: list[tuple[re.Pattern[str], str]] = []
        for alias, key in self.alias_to_key.items():
            # Escape regex special chars except for spaces which we convert to \s+
            escaped = re.escape(alias).replace("\\ ", r"\\s+")
            pattern = re.compile(boundary.format(escaped), re.IGNORECASE)
            self.alias_regex.append((pattern, key))

    def match_text(self, text: str) -> list[str]:
        if not text:
            return []
        matches: list[str] = []
        # Light normalization: collapse whitespace
        normalized = re.sub(r"\s+", " ", text)
        for pattern, key in self.alias_regex:
            if pattern.search(normalized):
                matches.append(key)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique = []
        for k in matches:
            if k not in seen:
                unique.append(k)
                seen.add(k)
        return unique

    def describe(self, key: str) -> Skill | None:
        return self.key_to_skill.get(key)
