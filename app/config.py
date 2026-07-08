import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve which .env file to load based on APP_ENV (set in shell or process env).
# Priority: APP_ENV shell variable → default to "development" → loads .env
# Examples:
#   APP_ENV=rnd      → loads .env.rnd
#   APP_ENV=qa       → loads .env.qa
#   APP_ENV=prod     → loads .env.prod
#   (unset)          → loads .env  (local development)
_APP_ENV = os.getenv("APP_ENV", "").strip().lower()
_ENV_FILE = f".env.{_APP_ENV}" if _APP_ENV else ".env"


# Database name suffixes per environment.
# If DATABASE_NAME is explicitly set in the .env file it takes priority;
# otherwise the name is derived automatically from the environment.
_DB_SUFFIX: dict[str, str] = {
    "rnd":  "interview_platform_rnd",
    "qa":   "interview_platform_qa",
    "prod": "interview_platform_prod",
}


class Settings(BaseSettings):
    MONGODB_URL: str = ""
    # DATABASE_NAME can be overridden in the .env file.
    # If not set, it is derived from APP_ENV (see validator below).
    DATABASE_NAME: str = ""
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Gmail SMTP credentials (use an App Password, NOT your real Gmail password)
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    FROM_EMAIL: str = ""          # defaults to GMAIL_USER if blank
    FRONTEND_URL: str = "http://localhost:5173"
    # ENVIRONMENT controls cookie security (development vs production).
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    def model_post_init(self, __context: object) -> None:
        """Derive DATABASE_NAME from APP_ENV if not explicitly set."""
        if not self.DATABASE_NAME:
            self.DATABASE_NAME = _DB_SUFFIX.get(_APP_ENV, "interview_platform_dev")


settings = Settings()
