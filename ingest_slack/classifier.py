from __future__ import annotations

import json
import os
from dataclasses import dataclass

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


DEFAULT_MODEL = "gpt-4o"


@dataclass(frozen=True)
class MessageCandidate:
    message_id: str
    author_id: str
    channel_id: str
    text: str
    parent_text: str | None
    skill_keys: tuple[str, ...]


@dataclass(frozen=True)
class SkillEvaluation:
    skill_key: str
    label: str  # positive_expertise | negative_expertise | neutral
    confidence: float
    rationale: str


@dataclass(frozen=True)
class MessageEvaluation:
    message_id: str
    author_id: str
    results: tuple[SkillEvaluation, ...]


_SYSTEM_PROMPT = (
    "You are an expert annotator. For each listed skill, classify whether the "
    "author demonstrates knowledge in THIS message."
    "\nLabel rules:\n"
    "- positive_expertise: the author provides guidance/solution/clear prior use "
    "or explains the concept/tool.\n"
    "- negative_expertise: the author states they don't know / are unsure / are "
    "new to the skill.\n"
    "- neutral: question asking, quoting others, off-topic mentions.\n"
    "Consider negation and quotes; do not attribute quoted text to the author."
)


def _build_user_prompt(candidate: MessageCandidate) -> str:
    parent = candidate.parent_text or ""
    skills = ", ".join(candidate.skill_keys)
    return (
        "Message:\n"
        f"{candidate.text}\n\n"
        + (f"Parent:\n{parent}\n\n" if parent else "")
        + "Classify these skills: "
        f"{skills}\n"
        + 'Return strict JSON: {"results": ['
        + '{"skill_key": str, "label": one of '
        + "[positive_expertise, negative_expertise, neutral], "
        + '"confidence": float 0..1, "rationale": str} ... ]}'
    )


def classify_messages(
    candidates: list[MessageCandidate],
    *,
    model: str | None = None,
) -> list[MessageEvaluation]:
    if not candidates:
        return []

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    if OpenAI is None:
        raise RuntimeError("openai package is not available")

    client = OpenAI(api_key=api_key)
    use_model = model or os.environ.get("CLASSIFIER_MODEL") or DEFAULT_MODEL

    evaluations: list[MessageEvaluation] = []
    for candidate in candidates:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(candidate)},
        ]

        resp = client.chat.completions.create(
            model=use_model,
            messages=messages,
            temperature=0.0,
        )

        raw = resp.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
            items = parsed.get("results", [])
        except Exception:
            items = []

        result_items: list[SkillEvaluation] = []
        for item in items:
            skill_key = str(item.get("skill_key", "")).strip()
            label = str(item.get("label", "neutral")).strip()
            try:
                confidence = float(item.get("confidence", 0.5))
            except Exception:
                confidence = 0.5
            rationale = str(item.get("rationale", "")).strip()
            if not skill_key:
                continue
            result_items.append(
                SkillEvaluation(
                    skill_key=skill_key,
                    label=label,
                    confidence=confidence,
                    rationale=rationale,
                )
            )

        evaluations.append(
            MessageEvaluation(
                message_id=candidate.message_id,
                author_id=candidate.author_id,
                results=tuple(result_items),
            )
        )

    return evaluations
