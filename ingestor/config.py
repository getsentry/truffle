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
    debug_sql: bool = Field(default=False, alias="DEBUG_SQL")

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

    # Scheduling
    ingestion_cron: str = "59 * * * *"

    # Slack API rate limiting (seconds between requests)
    slack_api_delay: float = Field(default=1.2, alias="SLACK_API_DELAY")

    # Batch-based rate limiting settings
    slack_batch_size: int = Field(default=50, alias="SLACK_BATCH_SIZE")
    slack_batch_wait_seconds: int = Field(default=61, alias="SLACK_BATCH_WAIT_SECONDS")
    slack_channel_delay_seconds: int = Field(
        default=61, alias="SLACK_CHANNEL_DELAY_SECONDS"
    )
    slack_rate_limit_delay_seconds: int = Field(
        default=61, alias="SLACK_RATE_LIMIT_DELAY_SECONDS"
    )

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
        if isinstance(self.debug_sql, str):
            self.debug_sql = self.debug_sql == "1"


# Global settings instance
settings = Settings()
