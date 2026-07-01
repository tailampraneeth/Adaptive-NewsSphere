"""
CategoryClassifierService — Automatic article category classification.

Uses a two-tier approach to minimise compute while maximising coverage:

  Tier 1 (Primary): Cosine similarity between the article embedding and
    pre-computed category anchor embeddings. If confidence >= 0.45, this
    result is returned.

  Tier 2 (Fallback): Lightweight keyword matching against a curated
    keyword map. Applied when embedding confidence is too low.

Supported categories (10):
  Technology, Business, Politics, Science, Health, Sports,
  Entertainment, Environment, World, Opinion

Design decisions:
  - Anchor embeddings are computed ONCE at startup and cached in memory.
  - The shared SentenceTransformer singleton is reused from embedder.py
    to avoid loading a second model into memory.
  - No paid APIs, no LLMs, no external calls — fully deterministic.

Usage:
  classifier = CategoryClassifierService()
  category, confidence = classifier.classify(article.title, article.body_text)
"""
import logging
import time
from typing import Tuple, Dict, Set, cast, Optional, Any
import numpy as np
from app.services.embedder import get_shared_model

logger = logging.getLogger("adaptive-newssphere.category_classifier")

# ── Category Definitions ────────────────────────────────────────────────────

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

# Representative anchor descriptions for each category.
# Multiple descriptions per category improve coverage by capturing different
# angles of the same topic domain.
CATEGORY_ANCHORS: Dict[str, list[str]] = {
    "Technology": [
        "technology software artificial intelligence machine learning computer programming",
        "smartphone gadget app tech startup cybersecurity cloud computing",
        "semiconductor chip GPU processor hardware electronics",
    ],
    "Business": [
        "business economy market stocks finance investment banking",
        "company earnings revenue profit CEO merger acquisition corporate",
        "startup funding venture capital IPO economy trade",
    ],
    "Politics": [
        "politics government election president congress senate law policy",
        "democracy parliament vote legislation political party campaign",
        "foreign policy diplomacy international relations sanctions",
    ],
    "Science": [
        "science research study discovery physics chemistry biology",
        "NASA space astronomy climate scientists experiment laboratory",
        "genome DNA neuroscience quantum mechanics breakthrough",
    ],
    "Health": [
        "health medicine hospital doctor patient vaccine drug treatment",
        "disease cancer diabetes mental health nutrition fitness exercise",
        "FDA clinical trial pharmaceutical drug approval healthcare",
    ],
    "Sports": [
        "sports football basketball soccer tennis golf Olympics athlete",
        "championship league tournament match score player coach team",
        "NBA NFL FIFA cricket formula racing motorsport",
    ],
    "Entertainment": [
        "entertainment movies film celebrity music concert award actor",
        "Hollywood streaming Netflix TV show series premiere director",
        "Grammy Oscar Emmy celebrity gossip music album release",
    ],
    "Environment": [
        "environment climate change global warming carbon emissions pollution",
        "renewable energy solar wind fossil fuel deforestation biodiversity",
        "sustainability green energy ocean conservation wildlife",
    ],
    "World": [
        "world international global news conflict war crisis humanitarian",
        "refugee migration disaster earthquake pandemic geopolitics",
        "United Nations Europe Asia Africa Middle East developing countries",
    ],
    "Opinion": [
        "opinion editorial commentary analysis perspective viewpoint",
        "argues believes claims suggests column essay debate",
        "review critique assessment judgment moral philosophical",
    ],
}

# Keyword fallback: lower-precision but zero compute
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
    """
    Two-tier article category classifier.

    Tier 1: Cosine similarity against pre-computed anchor embeddings.
    Tier 2: Keyword frequency fallback when confidence is below threshold.
    """

    # Minimum cosine similarity to use embedding result; below = keyword fallback
    EMBEDDING_CONFIDENCE_THRESHOLD = 0.45

    def __init__(self) -> None:
        logger.info("Initializing CategoryClassifierService...")
        t0 = time.time()
        self._model = get_shared_model()
        self._anchor_embeddings = self._precompute_anchors()
        logger.info(f"CategoryClassifierService ready in {time.time() - t0:.2f}s "
                    f"({len(CATEGORIES)} categories, {sum(len(v) for v in CATEGORY_ANCHORS.values())} anchors)")

    def _precompute_anchors(self) -> Dict[str, np.ndarray]:
        """
        Pre-computes and caches mean anchor embeddings for each category.
        Each category gets a single representative centroid vector.
        """
        anchors: Dict[str, np.ndarray] = {}
        for category, descriptions in CATEGORY_ANCHORS.items():
            vecs = self._model.encode(descriptions, convert_to_numpy=True)
            # Mean pooling — single centroid per category
            centroid = vecs.mean(axis=0)
            # L2 normalise for cosine similarity via dot product
            norm = np.linalg.norm(centroid)
            anchors[category] = cast(np.ndarray, centroid / (norm + 1e-9))
        return anchors

    async def classify(
        self,
        title: str,
        body_text: str,
        db: Optional[Any] = None,
        vector_store: Optional[Any] = None,
    ) -> Tuple[str, float]:
        """
        Classifies the article into one of 10 categories.

        Returns:
          (predicted_category, confidence)  where confidence ∈ [0.0, 1.0].

        Priority Strategy:
          1. Check embedding similarity against existing categorized articles (nearest neighbors >= 0.80).
          2. Check embedding similarity against pre-computed category anchor centroids (>= 0.45).
          3. Fall back to lightweight keyword frequency heuristics.
        """
        import uuid
        from sqlalchemy.future import select
        from app.database.models.article import Article

        combined = f"{title}. {body_text[:2000]}"

        try:
            # ── Priority 1: Check nearest neighbor similarity against categorized articles ──
            if vector_store and db:
                try:
                    vec_list = self._model.encode(combined, convert_to_numpy=True).tolist()
                    matches = vector_store.search_similar("articles", vec_list, top_k=3)
                    for match in matches:
                        if match["score"] >= 0.80:
                            match_uuid = uuid.UUID(str(match["id"]))
                            res = await db.execute(select(Article).where(Article.id == match_uuid))
                            matched_art = res.scalar_one_or_none()
                            if (
                                matched_art
                                and matched_art.category
                                and matched_art.category != "Uncategorized"
                            ):
                                logger.debug(
                                    f"Classified via nearest neighbor {matched_art.id} -> {matched_art.category} (score={match['score']:.3f})"
                                )
                                return matched_art.category, round(match["score"], 4)
                except Exception as nne:
                    logger.warning(f"Nearest-neighbor classification check bypassed: {nne}")

            # ── Priority 2: Check similarity against category anchor centroids ──
            vec = self._model.encode(combined, convert_to_numpy=True)
            norm = np.linalg.norm(vec)
            if norm < 1e-9:
                return self._keyword_fallback(title, body_text)

            vec_norm = vec / norm
            best_cat = "World"
            best_score = 0.0
            for cat, anchor in self._anchor_embeddings.items():
                score = float(np.dot(vec_norm, anchor))
                if score > best_score:
                    best_score = score
                    best_cat = cat

            if best_score >= self.EMBEDDING_CONFIDENCE_THRESHOLD:
                logger.debug(f"Classified '{title[:40]}' → {best_cat} (embedding, conf={best_score:.3f})")
                return best_cat, round(best_score, 4)

            # ── Tier 2: Keyword fallback ────────────────────────────────────────
            keyword_cat, keyword_conf = self._keyword_fallback(title, body_text)
            logger.debug(f"Classified '{title[:40]}' → {keyword_cat} (keyword, conf={keyword_conf:.3f})")
            return keyword_cat, keyword_conf

        except Exception as e:
            logger.error(f"Classification failed for '{title[:40]}': {e}")
            return "World", 0.10

    def _keyword_fallback(self, title: str, body_text: str) -> Tuple[str, float]:
        """
        Keyword frequency matching fallback.

        Counts keyword hits per category against lowercased title + first 500 chars
        of body. Returns the category with most hits. Confidence is proportional
        to hit density, capped at 0.44 (below embedding threshold by design).
        """
        text_lower = f"{title} {body_text[:500]}".lower()
        scores: Dict[str, int] = {}

        for cat, keywords in KEYWORD_MAP.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0:
                scores[cat] = hits

        if not scores:
            return "World", 0.10

        best_cat = max(scores, key=lambda c: scores[c])
        total_hits = scores[best_cat]
        # Confidence: 1 hit = 0.20, 2 = 0.30, 3+ scales up to max 0.44
        confidence = min(0.44, 0.20 + (total_hits - 1) * 0.08)
        return best_cat, round(confidence, 4)

    async def health(self) -> dict:
        """Service health check — classifies a known tech headline and asserts result."""
        try:
            t0 = time.time()
            cat, conf = await self.classify("Apple launches new iPhone with AI chip", "Technology")
            assert cat == "Technology", f"Expected Technology, got {cat}"
            latency = (time.time() - t0) * 1000
            return {
                "status": "PASS",
                "latency_ms": round(latency, 2),
                "details": {
                    "categories_loaded": len(CATEGORIES),
                    "anchors_precomputed": True,
                    "embedding_threshold": self.EMBEDDING_CONFIDENCE_THRESHOLD,
                }
            }
        except Exception as e:
            return {"status": "FAIL", "latency_ms": 0, "details": {"error": str(e)}}
