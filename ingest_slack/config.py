import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = os.environ.get(
        "TRUFFLE_DB_URL", "postgresql://user1:pass@localhost/truffle"
    )

    # Slack
    slack_bot_auth_token: str = os.environ.get("SLACK_BOT_AUTH_TOKEN", "")

    # OpenAI
    openai_api_key: str | None = os.environ.get("OPENAI_API_KEY")
    classifier_model: str = "gpt-4o"

    # Processing flags
    extract_skills: bool = os.environ.get("EXTRACT_SKILLS") == "1"
    classify_expertise: bool = os.environ.get("CLASSIFY_EXPERTISE") == "1"

    # Scheduling
    ingestion_cron: str = "*/1 * * * *"  # Every minute

    # Queue settings (for future scaling)
    redis_url: str = "redis://localhost:6379"
    queue_name: str = "slack_messages"

    class Config:
        env_file = ".env"


settings = Settings()
