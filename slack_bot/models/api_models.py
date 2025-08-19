"""API models for Slack bot endpoints"""

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class SlackEventsRequest(BaseModel):
    type: str | None = None
    event: dict[str, Any] | None = None
    challenge: str | None = None
    team_id: str | None = None
    api_app_id: str | None = None


class SlackEventsResponse(BaseModel):
    ok: bool
    message: str


class AskRequest(BaseModel):
    question: str
    context: str | None = None


class AskResponse(BaseModel):
    ok: bool
    answer: str
