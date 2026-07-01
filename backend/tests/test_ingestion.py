import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ingestion import IngestionService
from app.utils.text_cleaner import clean_html, generate_article_hashes

# Test fixtures are imported automatically from conftest.py

def test_html_cleaner():
    """Verify that html clean utilities strip scripts, tags, and normalize text whitespace."""
    dirty_html = "<html><body><script>alert('xss')</script><h1>Tech News</h1> <p>This is  clean. </p></body></html>"
    cleaned = clean_html(dirty_html)
    assert "alert('xss')" not in cleaned
    assert "Tech News This is clean." == cleaned

def test_hash_generation():
    """Confirm content and article hashes behave deterministically."""
    title = "Test Article Title"
    body = "Test body content."

    hash1_c, hash1_a = generate_article_hashes(title, body)
    hash2_c, hash2_a = generate_article_hashes(title, body)

    assert hash1_c == hash2_c
    assert hash1_a == hash2_a
    assert len(hash1_c) == 64  # SHA-256 length in hex representation

@pytest.mark.asyncio
async def test_duplicate_article_prevention(db_session: AsyncSession, monkeypatch):
    """Test that ingestion engine checks constraints and avoids duplicate DB records."""
    service = IngestionService(db_session)

    # 1. Register publisher
    await service.ensure_publisher("bbc", "BBC News", "https://www.bbc.com")

    # 2. Setup mock feed entries
    mock_feed = type("MockFeed", (), {
        "entries": [
            {
                "link": "https://www.bbc.com/news/1",
                "title": "Unique Article Title",
                "summary": "<p>Body content representation.</p>",
                "author": "Jane",
                "tags": [type("Tag", (), {"term": "Tech"})()]
            }
        ]
    })()

    # Monkeypatch feedparser.parse to return mock entries
    monkeypatch.setattr("feedparser.parse", lambda url: mock_feed)

    # First ingest call
    stats1 = await service.ingest_feed("bbc", "http://mock-url/feed")
    assert stats1["inserted"] == 1
    assert stats1["skipped_duplicate"] == 0

    # Second ingest call with same url feed payload
    stats2 = await service.ingest_feed("bbc", "http://mock-url/feed")
    assert stats2["inserted"] == 0
    assert stats2["skipped_duplicate"] == 1
