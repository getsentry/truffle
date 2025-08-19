"""Data models for Slack event processing"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SlackUser(BaseModel):
    """Slack user information"""

    id: str
    name: str | None = None
    display_name: str | None = None
    real_name: str | None = None


class SlackChannel(BaseModel):
    """Slack channel information"""

    id: str
    name: str | None = None
    is_private: bool = False
    is_im: bool = False


class ParsedSlackMessage(BaseModel):
    """Parsed Slack message with extracted information"""

    text: str
    cleaned_text: str  # Text with mentions/formatting removed
    user_id: str
    channel_id: str
    timestamp: str
    thread_ts: str | None = None

    # Extracted query information
    is_question: bool = False
    extracted_skills: list[str] = Field(default_factory=list)
    query_type: str | None = None  # "who_knows", "expert_search", "help", etc.

    # Message context
    is_app_mention: bool = False
    is_direct_message: bool = False
    mentioned_users: list[str] = Field(default_factory=list)

    # Metadata
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class SlackEventContext(BaseModel):
    """Context information for processing Slack events"""

    event_type: str
    event_id: str | None = None
    team_id: str | None = None
    api_app_id: str | None = None

    # Bot information
    bot_user_id: str | None = None
    bot_mentioned: bool = False

    # Processing metadata
    raw_event: dict[str, Any] = Field(default_factory=dict)
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExpertQuery(BaseModel):
    """Structured expert search query"""

    original_text: str
    skills: list[str]
    query_type: str  # "who_knows", "expert_for", "find_expert", etc.
    confidence: float = 0.0  # Confidence in the parsing

    # Optional filters
    exclude_users: list[str] = Field(default_factory=list)
    time_filter: str | None = None  # "recent", "all_time", etc.

    # Context
    user_id: str
    channel_id: str
    thread_ts: str | None = None
