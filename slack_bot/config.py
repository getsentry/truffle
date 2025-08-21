from pydantic import Field
from pydantic_settings import BaseSettings

VERSION = "1.0.0"


class Settings(BaseSettings):
    """Truffle Slack Bot configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    service_name: str = "Truffle Slack Bot"
    service_version: str = VERSION

    debug: bool = Field(default=False, alias="DEBUG")

    # Server configuration
    slack_bot_port: int = Field(default=8003, alias="SLACK_BOT_PORT")
    slack_bot_host: str = Field(default="0.0.0.0", alias="SLACK_BOT_HOST")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Service URLs
    expert_api_url: str = Field(default="http://localhost:8002", alias="EXPERT_API_URL")

    # Slack API Configuration
    slack_bot_auth_token: str = Field(default="", alias="SLACK_BOT_AUTH_TOKEN")
    slack_client_id: str = Field(default="", alias="SLACK_CLIENT_ID")
    slack_client_secret: str = Field(default="", alias="SLACK_CLIENT_SECRET")

    # Sentry configuration
    sentry_dsn: str | None = Field(default=None, alias="SLACK_BOT_SENTRY_DSN")

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
