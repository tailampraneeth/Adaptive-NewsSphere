import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    LOG_LEVEL: str = Field(default="INFO")
    APP_VERSION: str = Field(default="1.0.0")
    DEMO_MODE: bool = Field(default=False)

    # PostgreSQL Configuration
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5433)
    POSTGRES_DB: str = Field(default="newssphere")
    POSTGRES_USER: str = Field(default="developer")
    POSTGRES_PASSWORD: str = Field(default="LocalPassword123")

    # Database Connection URL (PostgreSQL asyncpg driver)
    DATABASE_URL: Optional[str] = Field(default=None)

    # Auth
    JWT_SECRET: str = Field(default="dev_secret_key_123_change_in_production")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080)  # 7 days

    # Ingestion & Summarization
    INGEST_SECRET: str = Field(default="default_ingest_secret_change_me")
    GEMINI_API_KEY: str = Field(default="mock_key_for_testing")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")

    # CORS
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")

    # Recommender Tuning
    COLD_START_MIN_READS: int = Field(default=3)
    COMPLETION_BOOST: float = Field(default=0.10)
    ABANDONMENT_PENALTY: float = Field(default=0.10)
    FRESHNESS_HALF_LIFE_HOURS: float = Field(default=24.0)

    # SMTP Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM_EMAIL: str = Field(default="no-reply@heimdall-watcher.com")
    FRONTEND_URL: str = Field(default="http://localhost:3000")

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        """Returns the PostgreSQL connection URL, constructing it if not supplied."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
