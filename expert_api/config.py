from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Truffle Expert API configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    # Database configuration
    database_url: str = Field(
        default="postgresql://truffle:truffle@localhost/truffle",
        alias="TRUFFLE_DB_URL",
    )

    # Server configuration
    expert_api_host: str = Field(default="0.0.0.0", alias="EXPERT_API_HOST")
    expert_api_port: int = Field(default=8002, alias="EXPERT_API_PORT")
    expert_api_workers: int = Field(default=1, alias="EXPERT_API_WORKERS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Service URLs
    ingestor_url: str = Field(default="http://localhost:8001", alias="INGESTOR_URL")
    slack_bot_url: str = Field(default="http://localhost:8003", alias="SLACK_BOT_URL")

    model_config = {
        "env_file": ".envrc",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }


# Global settings instance
settings = Settings()
