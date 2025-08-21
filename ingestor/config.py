from pydantic import Field
from pydantic_settings import BaseSettings

VERSION = "1.0.0"


class Settings(BaseSettings):
    """Truffle Ingestor configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    service_name: str = "Truffle Message Ingestion"
    service_version: str = VERSION

    debug: bool = Field(default=False, alias="DEBUG")

    # Server configuration
    ingestor_host: str = Field(default="0.0.0.0", alias="INGESTOR_HOST")
    ingestor_port: int = Field(default=8001, alias="INGESTOR_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database configuration
    database_url: str = Field(
        default="postgresql://truffle:truffle@localhost/truffle", alias="TRUFFLE_DB_URL"
    )

    # Slack API Configuration
    slack_bot_auth_token: str = Field(default="", alias="SLACK_BOT_AUTH_TOKEN")

    # OpenAI configuration
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    classifier_model: str = "gpt-4o"

    # Sentry configuration
    sentry_dsn: str | None = Field(default=None, alias="INGESTOR_SENTRY_DSN")

    # Processing flags

    # Service URLs
    expert_api_url: str = Field(default="http://localhost:8002", alias="EXPERT_API_URL")
    slack_bot_url: str = Field(default="http://localhost:8003", alias="SLACK_BOT_URL")

    # Scheduling
    ingestion_cron: str = "*/1 * * * *"  # Every 5 minutes

    model_config = {
        "env_file": ".envrc",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert string environment variables to boolean for flags
        if isinstance(self.debug, str):
            self.debug = self.debug == "1"


# Global settings instance
settings = Settings()
