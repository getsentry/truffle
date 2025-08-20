from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Truffle Ingestor configuration settings

    These settings can be configured via environment variables
    or .envrc files (loaded automatically by direnv).
    """

    # Database configuration
    database_url: str = Field(
        default="postgresql://truffle:truffle@localhost/truffle", alias="TRUFFLE_DB_URL"
    )

    # Slack API Configuration
    slack_bot_auth_token: str = Field(default="", alias="SLACK_BOT_AUTH_TOKEN")

    # OpenAI configuration
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    classifier_model: str = "gpt-4o"

    # Processing flags
    extract_skills: bool = Field(default=False, alias="EXTRACT_SKILLS")
    classify_expertise: bool = Field(default=False, alias="CLASSIFY_EXPERTISE")

    # Server configuration
    ingestor_host: str = Field(default="0.0.0.0", alias="INGESTOR_HOST")
    ingestor_port: int = Field(default=8001, alias="INGESTOR_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Service URLs
    expert_api_url: str = Field(default="http://localhost:8002", alias="EXPERT_API_URL")
    slack_bot_url: str = Field(default="http://localhost:8003", alias="SLACK_BOT_URL")

    # Scheduling
    ingestion_cron: str = "*/5 * * * *"  # Every 5 minutes

    model_config = {
        "env_file": ".envrc",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert string environment variables to boolean for flags
        if isinstance(self.extract_skills, str):
            self.extract_skills = self.extract_skills == "1"
        if isinstance(self.classify_expertise, str):
            self.classify_expertise = self.classify_expertise == "1"


# Global settings instance
settings = Settings()
