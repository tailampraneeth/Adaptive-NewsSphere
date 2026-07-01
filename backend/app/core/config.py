import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    LOG_LEVEL: str = Field(default="INFO")

    # PostgreSQL Configuration
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5433)
    POSTGRES_DB: str = Field(default="newssphere")
    POSTGRES_USER: str = Field(default="developer")
    POSTGRES_PASSWORD: str = Field(default="LocalPassword123")

    # Database Connection URL (PostgreSQL asyncpg driver)
    # If not supplied explicitly, we build it from components
    DATABASE_URL: Optional[str] = Field(default=None)

    # Cache Broker URL
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Qdrant URL
    QDRANT_URL: str = Field(default="http://localhost:6333")

    # Google Gemini API Key
    GEMINI_API_KEY: str = Field(default="mock_key_for_testing")

    # Semantic Clustering Thresholds (Phase 4)
    STORY_SIMILARITY_THRESHOLD: float = Field(default=0.82)
    STORY_MIN_CLUSTER_SIZE: int = Field(default=1)
    STORY_MAX_CLUSTER_SIZE: int = Field(default=100)

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        """Returns the PostgreSQL connection URL, constructing it if not supplied."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

# Singleton settings instance
settings = Settings()
