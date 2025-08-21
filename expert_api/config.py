from pydantic import Field
from pydantic_settings import BaseSettings

VERSION = "1.0.0"


class Settings(BaseSettings):
    """Truffle Expert API configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    service_name: str = "Truffle Expert Search API"
    service_version: str = VERSION

    debug: bool = Field(default=False, alias="DEBUG")

    # Server configuration
    expert_api_host: str = Field(default="0.0.0.0", alias="EXPERT_API_HOST")
    expert_api_port: int = Field(default=8002, alias="EXPERT_API_PORT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database configuration
    database_url: str = Field(
        default="postgresql://truffle:truffle@localhost/truffle",
        alias="TRUFFLE_DB_URL",
    )

    # Sentry configuration
    sentry_dsn: str | None = Field(default=None, alias="EXPERT_API_SENTRY_DSN")

    model_config = {
        "env_file": ".envrc",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert string environment variables to boolean for flags
        if isinstance(self.debug, str):
            self.debug = self.debug == "1"


# Global settings instance
settings = Settings()
