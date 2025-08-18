from __future__ import annotations

from fastapi import FastAPI

from models import (
    AskRequest,
    AskResponse,
    HealthResponse,
    SlackEventsRequest,
    SlackEventsResponse,
)

app = FastAPI(title="Slack Bot API")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/slack/events", response_model=SlackEventsResponse)
async def slack_events(_: SlackEventsRequest) -> SlackEventsResponse:
    return SlackEventsResponse(ok=True, message="slack events received")


@app.post("/ask", response_model=AskResponse)
async def ask(_: AskRequest) -> AskResponse:
    return AskResponse(ok=True, answer="example response")
