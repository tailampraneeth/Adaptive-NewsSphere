import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    LOG_LEVEL: str = Field(default="INFO")
    RANKING_ALGORITHM_VERSION: str = Field(default="v1")
    DEMO_MODE: bool = Field(default=False)

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

    # Semantic Clustering Thresholds
    STORY_SIMILARITY_THRESHOLD: float = Field(default=0.82)
    STORY_MIN_CLUSTER_SIZE: int = Field(default=1)
    STORY_MAX_CLUSTER_SIZE: int = Field(default=100)

    # ── Milestone 4: Recommendation Engine ───────────────────────────────────

    # Ranking Weights (must conceptually sum to ~1.0 for balanced scoring)
    # Tune these via environment variables without touching service code.
    SEMANTIC_WEIGHT: float = Field(default=0.50)       # Cosine sim vs user pref vector
    IMPORTANCE_WEIGHT: float = Field(default=0.25)     # Story importance signal
    TRENDING_WEIGHT: float = Field(default=0.15)       # Trending signal (live-decayed)
    CREDIBILITY_WEIGHT: float = Field(default=0.10)    # Publisher credibility score
    EXPLORATION_WEIGHT: float = Field(default=0.05)    # Random discovery bonus fraction

    # Freshness & Trending Decay Half-Lives
    FRESHNESS_DECAY_HALF_LIFE_HOURS: float = Field(default=24.0)  # t½ for story freshness
    TRENDING_DECAY_HALF_LIFE_HOURS: float = Field(default=6.0)    # t½ for trending signal

    # Cold-Start Threshold
    # Users with fewer than this many interactions receive cold-start ranking.
    COLD_START_THRESHOLD: int = Field(default=5)

    # EMA Interaction Weights (α values for preference vector updates)
    # Higher α = stronger pull toward the interacted story's embedding.
    EMA_WEIGHT_SHARE: float = Field(default=0.40)
    EMA_WEIGHT_BOOKMARK: float = Field(default=0.35)
    EMA_WEIGHT_DWELL_LONG: float = Field(default=0.20)   # dwell_seconds >= 60
    EMA_WEIGHT_CLICK: float = Field(default=0.15)
    EMA_WEIGHT_DWELL_SHORT: float = Field(default=0.05)  # dwell_seconds < 60

    # Negative Feedback Penalty Weights (applied as negative EMA α)
    # These push the preference vector away from the story's embedding.
    EMA_PENALTY_NOT_INTERESTED: float = Field(default=0.10)
    EMA_PENALTY_HIDE_STORY: float = Field(default=0.20)
    EMA_PENALTY_MUTE_CATEGORY: float = Field(default=0.30)
    EMA_PENALTY_MUTE_PUBLISHER: float = Field(default=0.40)

    # Multi-Axis Diversity Caps (per feed page)
    DIVERSITY_MAX_PER_CATEGORY: int = Field(default=4)
    DIVERSITY_MAX_PER_PUBLISHER: int = Field(default=3)
    DIVERSITY_MAX_PER_SOURCE_TYPE: int = Field(default=5)  # e.g., MAINSTREAM / WIRE_SERVICE

    # Redis preference cache TTL (seconds)
    PREFERENCE_CACHE_TTL_SECONDS: int = Field(default=604800)  # 7 days

    # ── Feature Flags ─────────────────────────────────────────────────────────
    # Toggle recommendation pipeline stages independently.
    # All default to True for full production behaviour.
    ENABLE_PERSONALIZATION: bool = Field(default=True)
    ENABLE_DIVERSITY: bool = Field(default=True)
    ENABLE_EXPLORATION: bool = Field(default=True)
    ENABLE_FRESHNESS_DECAY: bool = Field(default=True)
    ENABLE_TRENDING_DECAY: bool = Field(default=True)
    ENABLE_NEGATIVE_FEEDBACK: bool = Field(default=True)

    # ── Milestone 5: Conversational RAG ──────────────────────────────────────
    LLM_PROVIDER: str = Field(default="gemini")       # "gemini" | "mock"
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")
    RAG_TOP_K: int = Field(default=5)                  # Top articles to retrieve
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.55) # Min similarity score
    RAG_PROMPT_VERSION: str = Field(default="v1")
    RAG_MAX_CONTEXT_CHARS: int = Field(default=6000)   # Hard cap on context length
    RAG_MAX_HISTORY_MESSAGES: int = Field(default=10)  # History depth
    RAG_CHUNK_SIZE_CHARS: int = Field(default=1500)
    RAG_CHUNK_OVERLAP_CHARS: int = Field(default=300)
    ENABLE_RAG_STREAMING: bool = Field(default=True)
    ENABLE_RAG_CITATIONS: bool = Field(default=True)
    NO_CONTEXT_MESSAGE: str = Field(default="I do not have enough verified source information to answer this.")
    CONVERSATION_ENGINE_VERSION: str = Field(default="v1")

    # JWT Configuration
    JWT_SECRET: str = Field(default="dev_secret_key_123_change_in_production")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080)  # 7 days

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


# Singleton settings instance
settings = Settings()
