import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables.

    Sources (in priority order):
    1. Environment variables (e.g., from .envrc via direnv)
    2. .env file (fallback)
    3. Default values
    """

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

    # Server configuration
    ingestor_host: str = os.environ.get("INGESTOR_HOST", "0.0.0.0")
    ingestor_port: int = int(os.environ.get("INGESTOR_PORT", "8001"))
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

    # Scheduling
    ingestion_cron: str = "*/1 * * * *"  # Every minute

    # Queue settings (for future scaling)
    redis_url: str = "redis://localhost:6379"
    queue_name: str = "slack_messages"

    class Config:
        env_file = ".env"


settings = Settings()
