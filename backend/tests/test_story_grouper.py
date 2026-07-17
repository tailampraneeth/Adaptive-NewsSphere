import pytest
from datetime import datetime, timezone, timedelta
from app.database.models.article import Article
from app.database.models.story import Story
from app.services.story_grouper import StoryGrouperService


def test_story_grouper_jaccard_match():
    grouper = StoryGrouperService()

    now = datetime.now(timezone.utc)

    # Member article of story
    member_article = Article(
        publisher_id="reuters",
        title="Apple launches new iPhone with AI capabilities",
        published_at=now,
        predicted_category="Technology"
    )

    story = Story(
        title="Apple launches new iPhone with AI capabilities",
        predicted_category="Technology",
        last_updated_at=now,
        articles=[member_article]
    )

    # Similar headline, same category, same 12h window -> should match
    new_article = Article(
        publisher_id="bbc",
        title="New Apple iPhone launched with built-in AI chips",
        published_at=now + timedelta(hours=2),
        predicted_category="Technology",
        keywords=["apple", "iphone", "ai"]
    )

    matched_story, is_same_pub = grouper.cluster_article(new_article, [story])
    assert matched_story is not None
    assert is_same_pub is False


def test_story_grouper_different_category_no_match():
    grouper = StoryGrouperService()
    now = datetime.now(timezone.utc)

    member_article = Article(
        publisher_id="reuters",
        title="Apple launches new iPhone with AI capabilities",
        published_at=now,
        predicted_category="Technology"
    )

    story = Story(
        title="Apple launches new iPhone with AI capabilities",
        predicted_category="Technology",
        last_updated_at=now,
        articles=[member_article]
    )

    new_article = Article(
        publisher_id="bbc",
        title="Apple stocks drop ahead of iPhone launch",
        published_at=now,
        predicted_category="Business",  # different category
        keywords=["apple", "stocks"]
    )

    matched_story, _ = grouper.cluster_article(new_article, [story])
    assert matched_story is None


def test_story_grouper_same_publisher_flag():
    grouper = StoryGrouperService()
    now = datetime.now(timezone.utc)

    member_article = Article(
        publisher_id="reuters",
        title="Apple launches new iPhone with AI capabilities",
        published_at=now,
        predicted_category="Technology"
    )

    story = Story(
        title="Apple launches new iPhone with AI capabilities",
        predicted_category="Technology",
        last_updated_at=now,
        articles=[member_article]
    )

    # Same publisher (reuters) contributing update
    new_article = Article(
        publisher_id="reuters",
        title="Apple launches new iPhone with AI capabilities",
        published_at=now + timedelta(hours=1),
        predicted_category="Technology",
        keywords=["apple", "iphone"]
    )

    matched_story, is_same_pub = grouper.cluster_article(new_article, [story])
    assert matched_story is not None
    assert is_same_pub is True
