import hashlib
import logging
from datetime import date
from typing import Any

from config import settings
from services.skill_service import SkillService
from services.storage_service import StorageService

from .classifier import MessageCandidate, classify_messages

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self):
        self.skill_service = SkillService()
        self.storage = StorageService()
        # Thread context cache - in production this could be Redis
        self.thread_context: dict[str, dict[str, Any]] = {}

    async def process_message(
        self,
        message: dict[str, Any],
        channel: dict[str, Any],
        users: dict[str, dict[str, Any]],
    ):
        """Process a single message through the full pipeline"""

        # Skip if no user or text
        user_id = message.get("user")
        text = message.get("text", "")
        if not user_id or not text:
            return

        logger.debug(f"Processing message from {user_id}: {text[:100]}...")

        # 1. Extract skills
        if not settings.extract_skills:
            return

        matched_skills = await self.skill_service.match_text(text)
        if not matched_skills:
            logger.debug("No skills matched in message")
            return

        logger.debug(f"Matched skills: {matched_skills}")

        # 2. Handle thread context (inherit parent skills)
        combined_skills, parent_text = await self._handle_thread_context(
            message, matched_skills
        )

        # 3. Classify expertise if enabled
        if settings.classify_expertise and combined_skills:
            await self._classify_and_store(
                message, user_id, text, parent_text, combined_skills, channel
            )

    async def _handle_thread_context(
        self, message: dict[str, Any], matched_skills: list[str]
    ) -> tuple[list[str], str | None]:
        """Handle thread inheritance logic"""

        # Cache skills/text for parent messages (to be inherited by replies)
        reply_count = message.get("reply_count", 0)
        parent_id_for_parent = message.get("thread_ts") or message.get("ts")
        text_value = message.get("text", "")

        if reply_count > 0 and parent_id_for_parent:
            self.thread_context[parent_id_for_parent] = {
                "text": text_value,
                "skills": matched_skills,
            }

        # Inherit thread parent's skills for replies
        parent_text: str | None = None
        combined_keys = matched_skills
        is_reply = bool(message.get("thread_ts")) and message.get("ts") != message.get(
            "thread_ts"
        )

        if is_reply:
            parent_id = message.get("thread_ts", "")
            parent_ctx = self.thread_context.get(parent_id)
            if parent_ctx:
                parent_text = parent_ctx.get("text", "")
                inherited = parent_ctx.get("skills", [])
                if inherited:
                    # Combine skills without duplicates
                    seen = set()
                    combined_list = []
                    for k in list(matched_skills) + list(inherited):
                        if k not in seen:
                            combined_list.append(k)
                            seen.add(k)
                    combined_keys = combined_list

        return combined_keys, parent_text

    async def _classify_and_store(
        self,
        message: dict[str, Any],
        user_id: str,
        text: str,
        parent_text: str | None,
        skill_keys: list[str],
        channel: dict[str, Any],
    ):
        """Classify expertise and store evidence"""

        try:
            # Create message hash for deduplication
            message_content = f"{channel['id']}:{message.get('ts')}:{text}"
            message_hash = hashlib.sha256(message_content.encode()).hexdigest()[:16]

            # Classify expertise
            candidate = MessageCandidate(
                message_id=f"{channel['id']}:{message.get('ts')}",
                author_id=user_id,
                channel_id=channel["id"],
                text=text,
                parent_text=parent_text,
                skill_keys=tuple(skill_keys),
            )

            logger.debug(f"Classifying message for skills: {skill_keys}")
            evaluations = await classify_messages([candidate])

            # Store evidence in database
            if evaluations and evaluations[0].results:
                logger.info(
                    f"Storing {len(evaluations[0].results)} evidence items "
                    f"for user {user_id}"
                )
                await self.storage.store_expertise_evidence(
                    user_slack_id=user_id,
                    skill_keys=skill_keys,
                    evaluations=evaluations[0].results,
                    evidence_date=date.today(),
                    message_hash=message_hash,
                )
            else:
                logger.debug("No expertise evaluations to store")

        except Exception as e:
            logger.error(f"Failed to classify and store message: {e}", exc_info=True)
