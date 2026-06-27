import os
from app.core.config import Settings

def test_settings_load_defaults():
    """Verify that settings fallback to standard defaults when env is clean."""
    settings = Settings(DATABASE_URL=None)
    assert settings.LOG_LEVEL == "INFO"
    assert settings.POSTGRES_DB == "newssphere"
    assert "postgresql+asyncpg://" in settings.get_database_url()

def test_settings_custom_database_url():
    """Verify that overriding DATABASE_URL takes priority."""
    custom_url = "postgresql+asyncpg://test_user:pwd@remote-db:5432/test_db"
    settings = Settings(DATABASE_URL=custom_url)
    assert settings.get_database_url() == custom_url
