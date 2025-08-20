from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Truffle Slack Bot configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    # Server configuration
    slack_bot_port: int = Field(default=8003, alias="SLACK_BOT_PORT")
    slack_bot_host: str = Field(default="0.0.0.0", alias="SLACK_BOT_HOST")

    # Slack API Configuration
    slack_bot_auth_token: str = Field(default="", alias="SLACK_BOT_AUTH_TOKEN")

    # Service URLs
    ingestor_url: str = Field(default="http://localhost:8001", alias="INGESTOR_URL")
    expert_api_url: str = Field(default="http://localhost:8002", alias="EXPERT_API_URL")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_file": ".envrc",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }


# Global settings instance
settings = Settings()
