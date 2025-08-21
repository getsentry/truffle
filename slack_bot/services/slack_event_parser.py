"""Slack event parsing service"""

import logging
import re
from typing import Any

import sentry_sdk

from models.slack_models import ParsedSlackMessage, SlackEventContext

logger = logging.getLogger(__name__)


class SlackEventParser:
    """Parses Slack events and extracts relevant information"""

    def __init__(self, bot_user_id: str | None = None):
        self.bot_user_id = bot_user_id

        # Patterns for cleaning Slack messages
        self.mention_pattern = re.compile(r"<@[UW][A-Z0-9]+>")
        self.channel_pattern = re.compile(r"<#[C][A-Z0-9]+\|[^>]+>")
        self.url_pattern = re.compile(r"<https?://[^>]+>")
        self.formatting_pattern = re.compile(r"[*_~`]")

        # Question indicators
        self.question_indicators = [
            "who knows",
            "who is",
            "who can",
            "who has",
            "find expert",
            "find someone",
            "need help",
            "need expert",
            "need a",
            "need an",
            "looking for",
            "expert for",
            "expert in",
            "expert on",
            "help with",
            "advice on",
            "guidance on",
            "?",
        ]

    @sentry_sdk.trace
    def parse_event(self, event_data: dict[str, Any]) -> SlackEventContext | None:
        """Parse a Slack event and return context information"""
        try:
            event_type = event_data.get("type", "")

            context = SlackEventContext(
                event_type=event_type,
                event_id=event_data.get("event_id"),
                team_id=event_data.get("team_id"),
                api_app_id=event_data.get("api_app_id"),
                bot_user_id=self.bot_user_id,
                raw_event=event_data,
            )

            # Check if this is an event_callback with a nested event
            if event_type == "event_callback" and "event" in event_data:
                nested_event = event_data["event"]
                nested_type = nested_event.get("type", "")

                # Check if bot was mentioned
                if nested_type == "app_mention":
                    context.bot_mentioned = True
                elif nested_type == "message":
                    # Check if it's a DM or if bot was mentioned in the text
                    channel_type = nested_event.get("channel_type", "")
                    text = nested_event.get("text", "")

                    if channel_type == "im":
                        context.bot_mentioned = True
                    elif self.bot_user_id and f"<@{self.bot_user_id}>" in text:
                        context.bot_mentioned = True

            return context

        except Exception as e:
            logger.error(f"Error parsing Slack event: {e}")
            return None

    @sentry_sdk.trace
    def parse_message(self, event: dict[str, Any]) -> ParsedSlackMessage | None:
        """Parse a Slack message event into a structured format"""
        try:
            text = event.get("text", "")
            user_id = event.get("user", "")
            channel_id = event.get("channel", "")
            timestamp = event.get("ts", "")
            thread_ts = event.get("thread_ts")
            event_type = event.get("type", "")

            # Clean the message text
            cleaned_text = self._clean_message_text(text)

            # Extract mentioned users
            mentioned_users = self._extract_mentioned_users(text)

            # Determine message characteristics
            is_app_mention = event_type == "app_mention"
            is_direct_message = event.get("channel_type") == "im"
            is_question = self._is_question(cleaned_text)

            parsed_message = ParsedSlackMessage(
                text=text,
                cleaned_text=cleaned_text,
                user_id=user_id,
                channel_id=channel_id,
                timestamp=timestamp,
                thread_ts=thread_ts,
                is_question=is_question,
                is_app_mention=is_app_mention,
                is_direct_message=is_direct_message,
                mentioned_users=mentioned_users,
            )

            logger.info(f"Parsed message from {user_id}: '{cleaned_text[:50]}...'")
            return parsed_message

        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None

    @sentry_sdk.trace
    def _clean_message_text(self, text: str) -> str:
        """Clean Slack message text by removing mentions, links, and formatting"""
        # Remove user mentions
        text = self.mention_pattern.sub("", text)

        # Remove channel mentions
        text = self.channel_pattern.sub("", text)

        # Remove URLs
        text = self.url_pattern.sub("", text)

        # Remove formatting characters
        text = self.formatting_pattern.sub("", text)

        # Clean up whitespace
        text = " ".join(text.split())

        return text.strip()

    @sentry_sdk.trace
    def _extract_mentioned_users(self, text: str) -> list[str]:
        """Extract user IDs from mentions in the text"""
        mentions = self.mention_pattern.findall(text)
        user_ids = []

        for mention in mentions:
            # Extract user ID from <@U12345> format
            user_id = mention[2:-1]  # Remove <@ and >
            if user_id.startswith("U") or user_id.startswith("W"):
                user_ids.append(user_id)

        return user_ids

    def _is_question(self, text: str) -> bool:
        """Determine if the text appears to be a question"""
        text_lower = text.lower()

        # Check for question mark
        if "?" in text:
            return True

        # Check for question indicators
        for indicator in self.question_indicators:
            if indicator in text_lower:
                return True

        # Check for question word patterns at the beginning
        question_words = [
            "who",
            "what",
            "where",
            "when",
            "why",
            "how",
            "which",
            "can",
            "could",
            "would",
            "should",
        ]
        first_word = text_lower.split()[0] if text_lower.split() else ""

        return first_word in question_words

    def should_process_message(self, parsed_message: ParsedSlackMessage) -> bool:
        """Determine if this message should be processed for expert search"""
        # Process if it's a question and either:
        # 1. Bot was mentioned (@truffle)
        # 2. It's a direct message
        # 3. It contains expert-related keywords

        if not parsed_message.is_question:
            return False

        if parsed_message.is_app_mention or parsed_message.is_direct_message:
            return True

        # Check for expert-related keywords
        text_lower = parsed_message.cleaned_text.lower()
        expert_keywords = ["expert", "knows", "help with", "advice", "guidance"]

        return any(keyword in text_lower for keyword in expert_keywords)
