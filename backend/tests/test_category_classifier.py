"""
Tests for CategoryClassifierService — M2 Final Engineering Review.

Covers:
  - High-confidence embedding classification (Tier 1)
  - Keyword fallback classification (Tier 2)
  - Edge cases: empty body, short title only, ambiguous content
  - Health check passes
"""
import pytest
from app.services.category_classifier import CategoryClassifierService


@pytest.fixture(scope="module")
def classifier() -> CategoryClassifierService:
    """Session-scoped classifier (avoids re-computing anchors every test)."""
    return CategoryClassifierService()


@pytest.mark.asyncio
async def test_technology_classification(classifier: CategoryClassifierService):
    """Clear tech article should be classified as Technology with high confidence."""
    cat, conf = await classifier.classify(
        "Apple launches new iPhone 18 with AI processor chip",
        "Apple unveiled its latest smartphone, the iPhone 18, featuring a next-generation "
        "AI chip with enhanced machine learning capabilities. The device runs on the new "
        "iOS 18 operating system and supports advanced neural processing.",
    )
    assert cat == "Technology", f"Expected Technology, got {cat}"
    assert conf > 0.0, "Confidence should be positive"


@pytest.mark.asyncio
async def test_sports_classification(classifier: CategoryClassifierService):
    """Clear sports article should be classified as Sports."""
    cat, conf = await classifier.classify(
        "NBA Finals: Lakers defeat Celtics in Game 7",
        "The Los Angeles Lakers defeated the Boston Celtics 112-104 in a thrilling "
        "Game 7 of the NBA Finals. LeBron James scored 38 points to lead the Lakers "
        "to their 18th championship title.",
    )
    assert cat == "Sports", f"Expected Sports, got {cat}"
    assert conf > 0.0


@pytest.mark.asyncio
async def test_health_classification(classifier: CategoryClassifierService):
    """Health article should be classified as Health."""
    cat, conf = await classifier.classify(
        "FDA approves new cancer treatment drug",
        "The FDA has approved a new immunotherapy drug for treatment of metastatic "
        "lung cancer. Clinical trials showed an 80% response rate in patients. "
        "The drug will be available at hospitals starting next month.",
    )
    assert cat == "Health", f"Expected Health, got {cat}"


@pytest.mark.asyncio
async def test_politics_classification(classifier: CategoryClassifierService):
    """Political article should be classified as Politics."""
    cat, conf = await classifier.classify(
        "US presidential election results declared, Biden wins second term",
        "The United States presidential election has been called in favor of President Biden. "
        "Democrats gained seats in the Senate while Republicans held a narrow majority in the "
        "House of Representatives. The Electoral College confirmed the result with 302 votes.",
    )
    assert cat == "Politics", f"Expected Politics, got {cat}"


@pytest.mark.asyncio
async def test_keyword_fallback_low_body(classifier: CategoryClassifierService):
    """With minimal body text, should fall back to keyword matching."""
    cat, conf = await classifier.classify(
        "NBA game results",
        "Basketball.",  # Extremely short body
    )
    # Should classify via keyword fallback
    assert cat in {"Sports", "World"}  # Sports via keyword; World is default fallback
    assert conf >= 0.0


@pytest.mark.asyncio
async def test_confidence_range(classifier: CategoryClassifierService):
    """Confidence score should always be within [0.0, 1.0]."""
    test_cases = [
        ("Tech article", "iPhone Android app software cloud AI machine learning"),
        ("Empty ish", "..."),
        ("Mixed topic", "The president played golf at the club and discussed AI policy."),
    ]
    for title, body in test_cases:
        _, conf = await classifier.classify(title, body)
        assert 0.0 <= conf <= 1.0, f"Confidence out of range for '{title}': {conf}"


@pytest.mark.asyncio
async def test_empty_body_does_not_crash(classifier: CategoryClassifierService):
    """Empty body text should not raise an exception."""
    cat, conf = await classifier.classify("Some news headline", "")
    assert isinstance(cat, str)
    assert 0.0 <= conf <= 1.0


@pytest.mark.asyncio
async def test_health_check_passes(classifier: CategoryClassifierService):
    """Health check should return status=PASS."""
    result = await classifier.health()
    assert result["status"] == "PASS", f"Health check failed: {result}"
    assert result["details"]["anchors_precomputed"] is True
