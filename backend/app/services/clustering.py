"""
ClusteringService — Semantic story clustering engine.

Implements the core article-to-story grouping pipeline using vector similarity.
Each incoming article is:
  1. Checked for exact content duplicates (content_hash)
  2. Semantically embedded (title + body prefix via SentenceTransformer)
  3. Compared against the Qdrant "articles" collection via cosine similarity
  4. Either merged into an existing Story or used to spawn a new Story

New in M2 Final Review:
  - Story title: assigned from the article whose embedding is closest to centroid
  - Importance score: weighted composite signal (article_count, publisher diversity, freshness)
  - Trending score: recency-biased signal with 6h half-life decay
  - Duplicate classification: EXACT_DUPLICATE | SEMANTIC_DUPLICATE records written to article_duplicates
  - Formation evidence: structured JSON explaining cluster membership (for XAI)
  - Milestone 3 reserved: first_reported_at, last_updated_at updated on every cluster event
  - MetricsService integration: all phases timed

Architecture:
  - Qdrant "articles" collection: one vector per article (384-dim cosine)
  - Qdrant "stories" collection: one centroid vector per story (running average)
  - centroid_vector_id == str(story.id) — naming convention links both systems
"""
import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.database.models.article import Article
from app.database.models.duplicate import ArticleDuplicate
from app.database.models.story import Story
from app.services.embedder import EmbedderService
from app.services.metrics import get_metrics
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("adaptive-newssphere.clustering")

# ── Constants ────────────────────────────────────────────────────────────────

# Cosine threshold above which we upgrade a semantic duplicate to a provenance record
_SEMANTIC_DUPLICATE_THRESHOLD = 0.95

# Importance score weights (must sum to 1.0)
_W_ARTICLE_COUNT = 0.35
_W_PUBLISHER_DIV = 0.35
_W_FRESHNESS = 0.20
_W_CONFIDENCE = 0.10

# Half-lives for exponential decay (in hours)
_IMPORTANCE_HALF_LIFE_H = 24.0
_TRENDING_HALF_LIFE_H = 6.0


class ClusteringService:
    """
    Semantic story clustering engine.

    Groups related articles into Stories using vector similarity search.
    Maintains running centroid embeddings in Qdrant and quality signals in Postgres.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbedderService,
        vector_store: VectorStoreService,
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.vector_store = vector_store
        self.similarity_threshold = settings.STORY_SIMILARITY_THRESHOLD
        self._metrics = get_metrics()

    # ── Public API ────────────────────────────────────────────────────────────

    async def cluster_article(self, article: Article) -> Story:
        """
        Main entry point.  Processes a single article through the full pipeline:
          A. Exact duplicate detection (content_hash)
          B. Semantic embedding generation
          C. Qdrant similarity search
          D. Story assignment (merge into existing or create new)
          E. Story quality signal updates (scores, title, evidence)

        Returns:
          The Story the article was assigned to.
        """
        t_start = time.perf_counter()

        # A. Exact duplicate check ────────────────────────────────────────────
        dup_check = await self.db.execute(
            select(Article)
            .where(
                Article.content_hash == article.content_hash,
                Article.id != article.id,
            )
            .limit(1)
        )
        exact_dup = dup_check.scalars().first()

        if exact_dup and exact_dup.story_id:
            logger.info(
                f"Article {article.id} matches exact duplicate {exact_dup.id}. "
                f"Mapping to Story {exact_dup.story_id}."
            )
            story = await self._assign_exact_duplicate(article, exact_dup)
            self._metrics.record(
                "story_cluster",
                (time.perf_counter() - t_start) * 1000,
                {"path": "exact_duplicate"},
            )
            return story

        # Check if already marked as UPDATED_ARTICLE during ingestion
        if article.duplicate_type == "UPDATED_ARTICLE":
            # Find the original article it updated by matching the base source_url
            canonical_url = article.source_url.split("#updated-")[0]
            orig_check = await self.db.execute(
                select(Article).where(Article.source_url == canonical_url)
            )
            original_art = orig_check.scalars().first()
            if original_art and original_art.story_id:
                logger.info(
                    f"Article {article.id} is an update of original {original_art.id} in Story {original_art.story_id}."
                )

                # Fetch story
                story_res = await self.db.execute(
                    select(Story).where(Story.id == original_art.story_id)
                )
                story = story_res.scalar_one()

                # Link to same story
                article.story_id = story.id
                story.article_count += 1

                # Write to article_duplicates
                dup_record = ArticleDuplicate(
                    original_article_id=original_art.id,
                    duplicate_article_id=article.id,
                    duplicate_type="UPDATED_ARTICLE",
                    similarity_score=1.0,
                )
                self.db.add(dup_record)

                # Save its embedding in Qdrant anyway
                combined_text = f"{article.title}. {article.body_text[:1000]}"
                with self._metrics.measure("embedding_generate"):
                    vector = self.embedder.generate_embedding(combined_text)

                with self._metrics.measure("qdrant_index"):
                    article.qdrant_point_id = str(article.id)
                    self.vector_store.upsert_vector(
                        "articles",
                        str(article.id),
                        vector,
                        {
                            "publisher_id": article.publisher_id,
                            "category": article.category,
                            "language": article.language,
                        },
                    )

                # Update quality signals
                await self._update_story_quality(story)
                await self.db.commit()

                self._metrics.record(
                    "story_cluster",
                    (time.perf_counter() - t_start) * 1000,
                    {"path": "updated_article"},
                )
                return story

        # B. Generate embedding ────────────────────────────────────────────────
        combined_text = f"{article.title}. {article.body_text[:1000]}"
        with self._metrics.measure("embedding_generate"):
            vector = self.embedder.generate_embedding(combined_text)

        # Upsert article embedding to Qdrant
        with self._metrics.measure("qdrant_index"):
            article.qdrant_point_id = str(article.id)
            self.vector_store.upsert_vector(
                "articles",
                str(article.id),
                vector,
                {
                    "publisher_id": article.publisher_id,
                    "category": article.category,
                    "language": article.language,
                },
            )

        # C. Semantic similarity search ────────────────────────────────────────
        with self._metrics.measure("similarity_search"):
            similar_matches = self.vector_store.search_similar(
                "articles", vector, top_k=5
            )

        # D. Clustering decision ───────────────────────────────────────────────
        best_story_id, best_score, best_match_article = await self._find_best_story(
            article, similar_matches
        )

        if best_story_id:
            story = await self._merge_into_existing_story(
                article, vector, best_story_id, best_score, best_match_article
            )
        else:
            story = await self._create_new_story(article, vector)

        self._metrics.record(
            "story_cluster",
            (time.perf_counter() - t_start) * 1000,
            {"story_id": str(story.id), "path": "merge" if best_story_id else "new"},
        )
        return story

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _assign_exact_duplicate(
        self, article: Article, exact_dup: Article
    ) -> Story:
        """Links an exact-duplicate article to the original's story."""
        story_res = await self.db.execute(
            select(Story).where(Story.id == exact_dup.story_id)
        )
        story = story_res.scalar_one()

        # Generate and index its embedding anyway (needed for future similarity)
        vector = self.embedder.generate_embedding(
            f"{article.title}. {article.body_text[:1000]}"
        )
        article.qdrant_point_id = str(article.id)
        self.vector_store.upsert_vector(
            "articles",
            str(article.id),
            vector,
            {
                "publisher_id": article.publisher_id,
                "category": article.category,
                "language": article.language,
            },
        )

        article.story_id = story.id
        article.duplicate_type = "EXACT_DUPLICATE"
        article.quality_score *= 0.5  # duplicate penalty!
        story.article_count += 1

        # Write provenance record
        dup_record = ArticleDuplicate(
            original_article_id=exact_dup.id,
            duplicate_article_id=article.id,
            duplicate_type="EXACT_DUPLICATE",
            similarity_score=1.0,
        )
        self.db.add(dup_record)

        # Update quality signals
        await self._update_story_quality(story)
        await self.db.commit()
        return story

    async def _find_best_story(
        self,
        article: Article,
        similar_matches: List[Dict[str, Any]],
    ) -> Tuple[Optional[uuid.UUID], float, Optional[Article]]:
        """
        Scans similarity search results to find the highest-scoring existing story.

        Returns:
          (story_id, best_score, matched_article) or (None, 0.0, None) if no match.
        """
        best_story_id: Optional[uuid.UUID] = None
        best_score = 0.0
        best_match_article: Optional[Article] = None

        for match in similar_matches:
            if match["id"] == str(article.id):
                continue

            score: float = match["score"]
            if score > self.similarity_threshold and score > best_score:
                match_uuid = uuid.UUID(str(match["id"]))
                res = await self.db.execute(
                    select(Article).where(Article.id == match_uuid)
                )
                matched_art = res.scalar_one_or_none()

                if matched_art and matched_art.story_id:
                    best_story_id = matched_art.story_id
                    best_score = score
                    best_match_article = matched_art

        return best_story_id, best_score, best_match_article

    async def _merge_into_existing_story(
        self,
        article: Article,
        vector: List[float],
        story_id: uuid.UUID,
        similarity_score: float,
        original_article: Optional[Article],
    ) -> Story:
        """Merges the article into an existing story and updates all quality signals."""
        logger.info(
            f"Article '{article.title[:40]}' → existing Story {story_id} "
            f"(similarity={similarity_score:.3f})"
        )

        story_res = await self.db.execute(select(Story).where(Story.id == story_id))
        story = story_res.scalar_one()

        article.story_id = story.id
        story.article_count += 1

        # Record semantic duplicate provenance if very high similarity
        if similarity_score >= _SEMANTIC_DUPLICATE_THRESHOLD and original_article:
            article.duplicate_type = "SEMANTIC_DUPLICATE"
            article.quality_score *= 0.5  # duplicate penalty!
            dup_record = ArticleDuplicate(
                original_article_id=original_article.id,
                duplicate_article_id=article.id,
                duplicate_type="SEMANTIC_DUPLICATE",
                similarity_score=round(similarity_score, 6),
            )
            self.db.add(dup_record)
        elif (
            similarity_score >= 0.85
            and original_article
            and original_article.publisher_id == article.publisher_id
        ):
            # Check if title or body contains correction indicators
            correction_words = {"correction", "retraction", "clarification", "corrigendum", "amendment", "update"}
            text_lower = f"{article.title} {article.body_text[:200]}".lower()
            if any(word in text_lower for word in correction_words):
                article.duplicate_type = "CORRECTED_ARTICLE"
                dup_record = ArticleDuplicate(
                    original_article_id=original_article.id,
                    duplicate_article_id=article.id,
                    duplicate_type="CORRECTED_ARTICLE",
                    similarity_score=round(similarity_score, 6),
                )
                self.db.add(dup_record)

        # Update running-average centroid in Qdrant
        centroid = await self._calculate_updated_centroid(story, vector)
        self.vector_store.upsert_vector(
            "stories",
            str(story.id),
            centroid,
            {"article_count": story.article_count},
        )
        story.centroid_vector_id = str(story.id)

        # Update all quality signals
        await self._update_story_quality(story)
        await self.db.commit()
        return story

    async def _create_new_story(
        self, article: Article, vector: List[float]
    ) -> Story:
        """Creates a new Story seeded by the given article."""
        logger.info(
            f"No match above threshold {self.similarity_threshold}. "
            f"Creating new Story for '{article.title[:40]}'..."
        )

        new_story = Story(
            id=uuid.uuid4(),
            title=article.title,
            summary=article.body_text[:1000] if article.body_text else "No content.",
            status="ACTIVE",
            confidence_score=1.00,
            article_count=1,
            importance_score=0.0,
            trending_score=0.0,
            first_reported_at=article.published_at,
            last_updated_at=article.published_at,
        )
        self.db.add(new_story)
        await self.db.flush()  # Flush to get new_story.id

        article.story_id = new_story.id

        # First article's vector IS the initial centroid
        self.vector_store.upsert_vector(
            "stories",
            str(new_story.id),
            vector,
            {"article_count": 1},
        )
        new_story.centroid_vector_id = str(new_story.id)

        # Compute initial quality signals
        await self._update_story_quality(new_story)
        await self.db.commit()
        return new_story

    # ── Story Quality Computations ────────────────────────────────────────────

    async def _update_story_quality(self, story: Story) -> None:
        """
        Master update method — calls all quality signal updaters.
        Called after every cluster event (merge or new story creation).
        """
        res = await self.db.execute(select(Article).where(Article.story_id == story.id))
        articles = list(res.scalars().all())

        await self._update_story_summary(story, articles)
        rep_article = await self._update_story_title(story, articles)

        if rep_article:
            story.representative_article_id = rep_article.id

        unique_publishers = {a.publisher_id for a in articles}
        story.publisher_diversity = len(unique_publishers)

        self._update_importance_score(story, articles)
        self._update_trending_score(story, articles)
        self._update_formation_evidence(story, articles)

        # Expose a structured context object for future Retrieval-Augmented Generation (RAG)
        if articles:
            rep_art = rep_article or articles[0]
            story.rag_context = {
                "representative_article": {
                    "id": str(rep_art.id),
                    "title": rep_art.title,
                    "body_text": rep_art.body_text[:2000] if rep_art.body_text else "",
                    "publisher": rep_art.publisher_id
                },
                "summary": story.summary,
                "keywords": story.formation_evidence.get("shared_keywords", []) if story.formation_evidence else [],
                "named_entities": story.formation_evidence.get("shared_entities", {}) if story.formation_evidence else {},
                "topics": story.formation_evidence.get("shared_topics", []) if story.formation_evidence else []
            }

        self._update_milestone3_fields(story, articles)

    async def _update_story_summary(
        self, story: Story, articles: List[Article]
    ) -> None:
        """
        Deterministic summary: body[:1000] of the longest article.
        """
        try:
            if articles:
                longest = max(
                    articles, key=lambda a: len(a.body_text) if a.body_text else 0
                )
                story.summary = (
                    longest.body_text[:1000] if longest.body_text else "No content."
                )
        except Exception as e:
            logger.error(f"Failed to update summary for Story {story.id}: {e}")

    async def _update_story_title(
        self, story: Story, articles: List[Article]
    ) -> Optional[Article]:
        """
        Assigns the story title from the article whose embedding is closest to
        the current centroid vector (deterministic, no LLM).

        For a single-article story, uses the article title directly.
        For multi-article stories, finds the centroid-nearest article.
        """
        try:
            if not articles:
                return None

            if len(articles) == 1:
                story.title = articles[0].title
                return articles[0]

            # Retrieve the current centroid vector from Qdrant
            points = self.vector_store.client.retrieve(
                collection_name="stories",
                ids=[str(story.id)],
                with_vectors=True,
            )
            if not points or not points[0].vector:
                story.title = articles[0].title
                return articles[0]

            centroid_vec = points[0].vector
            if not isinstance(centroid_vec, list):
                story.title = articles[0].title
                return articles[0]

            centroid_arr = np.array(centroid_vec, dtype=np.float32)
            centroid_norm = centroid_arr / (np.linalg.norm(centroid_arr) + 1e-9)

            # Find the article whose embedding is nearest the centroid
            best_article: Optional[Article] = None
            best_sim = -1.0
            for art in articles:
                if not art.qdrant_point_id:
                    continue
                try:
                    art_points = self.vector_store.client.retrieve(
                        collection_name="articles",
                        ids=[str(art.id)],
                        with_vectors=True,
                    )
                    if art_points and art_points[0].vector and isinstance(art_points[0].vector, list):
                        art_arr = np.array(art_points[0].vector, dtype=np.float32)
                        art_norm = art_arr / (np.linalg.norm(art_arr) + 1e-9)
                        sim = float(np.dot(centroid_norm, art_norm))
                        if sim > best_sim:
                            best_sim = sim
                            best_article = art
                except Exception:
                    continue

            if best_article:
                story.title = best_article.title
                return best_article
            else:
                story.title = articles[0].title
                return articles[0]

        except Exception as e:
            logger.error(f"Failed to update title for Story {story.id}: {e}")
            if articles:
                story.title = articles[0].title
                return articles[0]
            return None

    def _update_importance_score(
        self, story: Story, articles: List[Article]
    ) -> None:
        """
        Importance score (0.0–1.0) — composite weighted signal for recommendations.

        Formula:
          importance = (article_count_score * 0.35) +
                       (publisher_diversity_score * 0.35) +
                       (freshness_score * 0.20) +
                       (confidence_score * 0.10)
        """
        try:
            # Article count score: normalised at 20 articles = 1.0
            article_count_score = min(1.0, story.article_count / 20.0)

            # Publisher diversity: normalised at 5 unique publishers = 1.0
            unique_publishers = len({a.publisher_id for a in articles})
            publisher_div_score = min(1.0, unique_publishers / 5.0)

            # Freshness: exponential decay with 24h half-life
            freshness_score = self._compute_decay(articles, _IMPORTANCE_HALF_LIFE_H)

            # Confidence (direct from story model)
            confidence = float(story.confidence_score)

            importance = (
                article_count_score * _W_ARTICLE_COUNT
                + publisher_div_score * _W_PUBLISHER_DIV
                + freshness_score * _W_FRESHNESS
                + confidence * _W_CONFIDENCE
            )
            story.importance_score = round(min(1.0, importance), 6)

        except Exception as e:
            logger.error(f"Failed to compute importance for Story {story.id}: {e}")

    def _update_trending_score(
        self, story: Story, articles: List[Article]
    ) -> None:
        """
        Trending score (0.0–1.0) — recency-biased signal with 6h half-life.

        Formula:
          trending = (recency_score * 0.40) +
                     (growth_rate_score * 0.30) +
                     (publisher_diversity_score * 0.30)
        """
        try:
            # Recency: 6h half-life decay from newest article
            recency_score = self._compute_decay(articles, _TRENDING_HALF_LIFE_H)

            # Growth rate: articles published in last 24h, normalised at 10 = 1.0
            now = datetime.now(timezone.utc)
            recent_articles = [
                a for a in articles
                if a.published_at
                and (now - a.published_at.replace(tzinfo=timezone.utc
                     if a.published_at.tzinfo is None else a.published_at.tzinfo)
                     ).total_seconds() < 86400
            ]
            growth_rate_score = min(1.0, len(recent_articles) / 10.0)

            # Publisher diversity (same formula as importance)
            unique_publishers = len({a.publisher_id for a in articles})
            publisher_div_score = min(1.0, unique_publishers / 5.0)

            trending = (
                recency_score * 0.40
                + growth_rate_score * 0.30
                + publisher_div_score * 0.30
            )
            story.trending_score = round(min(1.0, trending), 6)

        except Exception as e:
            logger.error(f"Failed to compute trending for Story {story.id}: {e}")

    def _update_formation_evidence(
        self, story: Story, articles: List[Article]
    ) -> None:
        """
        Builds structured XAI evidence explaining why articles belong together.

        Schema:
          {
            "shared_keywords": list[str],       # intersection of top keywords
            "shared_entities": {                 # merged entity intersection
              "organizations": list[str],
              "persons": list[str],
              "locations": list[str]
            },
            "shared_topics": list[str],          # intersection of topics
            "avg_similarity_score": float,       # confidence_score proxy
            "article_count": int,
            "publisher_count": int
          }
        """
        try:
            if not articles:
                return

            # Aggregate keywords across all articles
            all_keywords: List[List[str]] = [
                a.keywords for a in articles if a.keywords  # type: ignore[misc]
            ]
            # Find keywords that appear in at least 2 articles (shared evidence)
            if all_keywords:
                from collections import Counter
                kw_flat = [kw for kws in all_keywords for kw in kws]
                shared_kws = [kw for kw, cnt in Counter(kw_flat).items() if cnt >= 2][:10]
            else:
                shared_kws = []

            # Aggregate entities
            all_orgs: List[str] = []
            all_persons: List[str] = []
            all_locs: List[str] = []
            for a in articles:
                if a.named_entities:
                    ents = a.named_entities
                    all_orgs.extend(ents.get("organizations", []))
                    all_persons.extend(ents.get("persons", []))
                    all_locs.extend(ents.get("locations", []))

            from collections import Counter as Ctr
            shared_orgs = [e for e, cnt in Ctr(all_orgs).items() if cnt >= 2][:8]
            shared_persons = [e for e, cnt in Ctr(all_persons).items() if cnt >= 2][:8]
            shared_locs = [e for e, cnt in Ctr(all_locs).items() if cnt >= 2][:8]

            # Topics
            all_topics_flat = [t for a in articles if a.topics for t in a.topics]  # type: ignore[union-attr]
            shared_topics = [t for t, cnt in Ctr(all_topics_flat).items() if cnt >= 2][:5]

            story.formation_evidence = {
                "shared_keywords": shared_kws,
                "shared_entities": {
                    "organizations": shared_orgs,
                    "persons": shared_persons,
                    "locations": shared_locs,
                },
                "shared_topics": shared_topics,
                "avg_similarity_score": float(story.confidence_score),
                "article_count": story.article_count,
                "publisher_count": len({a.publisher_id for a in articles}),
            }

        except Exception as e:
            logger.error(f"Failed to build formation evidence for Story {story.id}: {e}")

    def _update_milestone3_fields(
        self, story: Story, articles: List[Article]
    ) -> None:
        """
        Maintains Milestone 3 reserved timeline fields.
        first_reported_at → earliest published_at in cluster.
        last_updated_at   → most recent published_at in cluster.
        """
        try:
            published_times = [
                a.published_at for a in articles if a.published_at is not None
            ]
            if published_times:
                story.first_reported_at = min(published_times)
                story.last_updated_at = max(published_times)
        except Exception as e:
            logger.error(f"Failed to update Milestone 3 fields for Story {story.id}: {e}")

    async def _calculate_updated_centroid(
        self, story: Story, new_vector: List[float]
    ) -> List[float]:
        """
        Computes the running average centroid:
          centroid_new = (centroid_old * old_count + new_vector) / article_count
        """
        try:
            points = self.vector_store.client.retrieve(
                collection_name="stories",
                ids=[str(story.id)],
                with_vectors=True,
            )
            if points and points[0].vector:
                old_centroid = points[0].vector
                if isinstance(old_centroid, list):
                    old_count = max(1, story.article_count - 1)
                    arr_old = np.array(old_centroid, dtype=np.float32)
                    arr_new = np.array(new_vector, dtype=np.float32)
                    new_centroid = ((arr_old * old_count) + arr_new) / story.article_count
                    result_list: List[float] = cast(Any, new_centroid).tolist()
                    return result_list
        except Exception as e:
            logger.error(f"Error calculating centroid for Story {story.id}: {e}")

        return new_vector

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_decay(articles: List[Article], half_life_hours: float) -> float:
        """
        Computes exponential freshness decay based on the most recent article.

        decay = 2^(-age_hours / half_life_hours)

        Returns 1.0 if no articles, 1.0 for brand-new, ~0.0 for very old.
        """
        if not articles:
            return 1.0

        now = datetime.now(timezone.utc)
        valid_times = []
        for a in articles:
            if a.published_at:
                ts = a.published_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                valid_times.append(ts)

        if not valid_times:
            return 1.0

        newest = max(valid_times)
        age_seconds = (now - newest).total_seconds()
        age_hours = max(0.0, age_seconds / 3600.0)
        return math.pow(2.0, -age_hours / half_life_hours)

    def health(self) -> dict:
        """Service health check — returns status and current config."""
        return {
            "status": "PASS",
            "latency_ms": 0.0,
            "details": {
                "similarity_threshold": self.similarity_threshold,
                "vector_store_healthy": self.vector_store.health()["status"] == "PASS",
            },
        }
