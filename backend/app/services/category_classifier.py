"""
CategoryClassifierService — Automatic article category classification.
Heimdall Consumer Edition: pure keyword-based, zero embedding dependencies.
"""
import logging
from typing import Tuple, Dict, Set, Optional, Any

logger = logging.getLogger("heimdall.category_classifier")

CATEGORIES = [
    "Technology",
    "Business",
    "Politics",
    "Science",
    "Health",
    "Sports",
    "Entertainment",
    "Environment",
    "World",
    "Opinion",
]

KEYWORD_MAP: Dict[str, Set[str]] = {
    "Technology": {
        "ai", "tech", "software", "app", "robot", "algorithm", "data", "cloud",
        "startup", "silicon", "chip", "cybersecurity", "hack", "digital", "internet",
        "smartphone", "iphone", "android", "gpu", "machine learning", "neural",
        "openai", "google", "microsoft", "apple", "meta", "amazon",
    },
    "Business": {
        "market", "stock", "ceo", "revenue", "profit", "company", "investor",
        "bank", "economy", "fund", "equity", "merger", "acquisition", "ipo",
        "wall street", "nasdaq", "dow", "trading", "financial", "earnings",
    },
    "Politics": {
        "president", "congress", "senate", "election", "vote", "democrat",
        "republican", "parliament", "government", "policy", "law", "minister",
        "white house", "campaign", "ballot", "legislation", "political",
    },
    "Science": {
        "research", "study", "nasa", "space", "scientist", "discovery",
        "experiment", "laboratory", "physics", "chemistry", "biology",
        "climate", "genome", "dna", "neuroscience", "quantum", "universe",
    },
    "Health": {
        "health", "hospital", "doctor", "vaccine", "drug", "disease", "cancer",
        "diabetes", "mental health", "patient", "treatment", "fda", "clinical",
        "medicine", "fitness", "nutrition", "pandemic", "virus", "infection",
    },
    "Sports": {
        "nba", "nfl", "fifa", "olympic", "athlete", "championship", "league",
        "tournament", "football", "basketball", "soccer", "tennis", "cricket",
        "match", "score", "player", "coach", "team", "stadium",
    },
    "Entertainment": {
        "movie", "film", "oscar", "emmy", "grammy", "celebrity", "actor",
        "director", "netflix", "streaming", "music", "album", "concert",
        "hollywood", "tv show", "series", "premiere", "award", "singer",
    },
    "Environment": {
        "climate", "carbon", "emission", "pollution", "renewable", "solar",
        "wind", "fossil", "conservation", "biodiversity", "ecosystem",
        "deforestation", "sustainability", "green", "wildfire", "ocean",
    },
    "World": {
        "war", "conflict", "refugee", "crisis", "disaster", "earthquake",
        "humanitarian", "united nations", "nato", "europe", "asia", "africa",
        "china", "russia", "ukraine", "india", "middle east", "migration",
    },
    "Opinion": {
        "opinion", "editorial", "commentary", "analysis", "argues", "believes",
        "perspective", "column", "essay", "debate", "critique", "viewpoint",
        "should", "must", "wrong", "right", "moral",
    },
}


class CategoryClassifierService:
    """Keyword frequency based category classifier."""

    def __init__(self) -> None:
        logger.info("Initializing CategoryClassifierService (keyword-only)...")

    async def classify(
        self,
        title: str,
        body_text: str,
        db: Optional[Any] = None,
        vector_store: Optional[Any] = None,
    ) -> Tuple[str, float]:
        """
        Classifies the article into one of 10 categories.
        Returns (predicted_category, confidence)
        """
        return self._keyword_classify(title, body_text)

    def _keyword_classify(self, title: str, body_text: str) -> Tuple[str, float]:
        text_lower = f"{title} {body_text[:1000]}".lower()
        scores: Dict[str, int] = {}

        for cat, keywords in KEYWORD_MAP.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0:
                scores[cat] = hits

        if not scores:
            return "World", 0.10

        best_cat = max(scores, key=lambda c: scores[c])
        total_hits = scores[best_cat]
        # Confidence logic: 1 hit = 0.20, 2 = 0.30, 3+ = 0.44
        confidence = min(0.44, 0.20 + (total_hits - 1) * 0.10)
        return best_cat, round(confidence, 4)

    async def health(self) -> dict:
        """Service health check."""
        try:
            cat, conf = await self.classify("Apple launches new iPhone with AI chip", "Technology")
            assert cat == "Technology", f"Expected Technology, got {cat}"
            return {
                "status": "PASS",
                "details": {
                    "categories_loaded": len(CATEGORIES),
                }
            }
        except Exception as e:
            return {"status": "FAIL", "details": {"error": str(e)}}
