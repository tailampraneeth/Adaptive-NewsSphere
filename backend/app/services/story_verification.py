import logging
import re
import uuid
import numpy as np
import spacy
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete

from app.database.models.story import Story, StoryRelation
from app.database.models.publisher import Publisher
from app.database.models.timeline import StoryTimeline
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

class StoryVerificationService:
    """
    Implements deterministic, CPU-friendly Story Intelligence & Verification.
    Calculates agreement/contradiction scores, publisher credibility indexes, evidence
    registries, chronological timeline evolution, and directed graph relationships (RELATED/FOLLOW_UP).
    Does NOT use paid LLM APIs.
    """
    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbedderService,
        vector_store: VectorStoreService
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.vector_store = vector_store
        self.nlp: Optional[spacy.Language] = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            logger.warning("spaCy model en_core_web_sm not loaded. Falling back to basic sentence splitting.")
            self.nlp = None

    async def verify_story(self, story_id: uuid.UUID) -> None:
        """
        Performs full verification, credibility scoring, evidence compiling,
        timeline generation, and story graph relationship linking.
        """
        stmt = (
            select(Story)
            .where(Story.id == story_id)
            .options(
                selectinload(Story.articles),
                selectinload(Story.representative_article)
            )
        )
        res = await self.db.execute(stmt)
        story = res.scalar_one_or_none()
        if not story:
            logger.error(f"Story {story_id} not found in database.")
            return

        articles = story.articles
        if not articles:
            return

        # ── Maintain first/last reported timestamps ──
        pub_times = [a.published_at for a in articles if a.published_at]
        if pub_times:
            story.first_reported_at = min(pub_times)
            story.last_updated_at = max(pub_times)

        # Handle single-source or cold-start stories (no multi-source comparison possible)
        if len(articles) <= 1:
            story.verification_score = 1.0
            story.has_conflicts = False
            # Credibility defaults to publisher score
            art = articles[0]
            stmt_p = select(Publisher).where(Publisher.id == art.publisher_id)
            res_p = await self.db.execute(stmt_p)
            pub = res_p.scalar_one_or_none()
            story.credibility_score = float(pub.credibility_score) if pub else 0.90

            # Evidence mapping
            story.evidence = [{
                "publisher_id": art.publisher_id,
                "credibility": float(pub.credibility_score) if pub else 0.90,
                "article_title": art.title,
                "article_hash": art.article_hash
            }]
            story.formation_evidence = {
                "similarity_threshold": 0.82,
                "supporting_publishers_count": 1,
                "has_conflicts": False,
                "conflicts": []
            }

            await self.generate_timeline(story)
            await self.update_graph_relationships(story)
            await self.db.commit()
            return

        # ── Step 1: Claim extraction & semantic comparisons ──
        claims: List[Dict[str, Any]] = []
        for art in articles:
            body = art.body_text or ""
            # Extract sentences
            if self.nlp:
                doc = self.nlp(body)
                sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 30]
            else:
                sentences = [s.strip() for s in body.split(".") if len(s.strip()) > 30]

            for s in sentences[:15]:  # limit sentences per article to optimize CPU/time
                claims.append({
                    "text": s,
                    "publisher_id": art.publisher_id,
                    "article_id": art.id
                })

        agreement_count = 0
        contradiction_count = 0
        conflicts_list = []
        verified_claims_count = 0
        total_claims_checked = 0

        if claims:
            texts = [c["text"] for c in claims]
            try:
                vectors = self.embedder.generate_embeddings_batch(texts)
                for i in range(len(claims)):
                    total_claims_checked += 1
                    found_match = False

                    vec_a = np.array(vectors[i], dtype=np.float32)
                    norm_a = np.linalg.norm(vec_a)

                    for j in range(len(claims)):
                        if claims[i]["publisher_id"] == claims[j]["publisher_id"]:
                            continue

                        vec_b = np.array(vectors[j], dtype=np.float32)
                        norm_b = np.linalg.norm(vec_b)
                        if norm_a > 1e-9 and norm_b > 1e-9:
                            similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
                        else:
                            similarity = 0.0

                        if similarity >= 0.75:
                            found_match = True
                            agreement_count += 1
                            break

                    if found_match:
                        verified_claims_count += 1
                    else:
                        # If no agreement match, check for contradictions
                        # Compare against other publishers' sentences to find the closest semantic context
                        best_overlap = 0.0
                        target_idx = -1

                        for j in range(len(claims)):
                            if claims[i]["publisher_id"] == claims[j]["publisher_id"]:
                                continue

                            nouns_a = self._extract_key_words(claims[i]["text"])
                            nouns_b = self._extract_key_words(claims[j]["text"])

                            union = nouns_a.union(nouns_b)
                            intersection = nouns_a.intersection(nouns_b)
                            jaccard = len(intersection) / len(union) if union else 0.0

                        for j in range(len(claims)):
                            if claims[i]["publisher_id"] == claims[j]["publisher_id"]:
                                continue

                            nouns_a = self._extract_key_words(claims[i]["text"])
                            nouns_b = self._extract_key_words(claims[j]["text"])

                            union = nouns_a.union(nouns_b)
                            intersection = nouns_a.intersection(nouns_b)
                            jaccard = len(intersection) / len(union) if union else 0.0

                            if jaccard > best_overlap:
                                best_overlap = jaccard
                                target_idx = j

                        if best_overlap >= 0.40 and target_idx != -1:
                            vec_b = np.array(vectors[target_idx], dtype=np.float32)
                            norm_b = np.linalg.norm(vec_b)
                            if norm_a > 1e-9 and norm_b > 1e-9:
                                similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
                            else:
                                similarity = 0.0

                            if similarity < 0.40:
                                contradiction_count += 1
                                # Audit numbers
                                nums_a = self._extract_numbers(claims[i]["text"])
                                nums_b = self._extract_numbers(claims[target_idx]["text"])
                                if nums_a != nums_b and nums_a and nums_b:
                                    story.has_conflicts = True
                                    conflicts_list.append({
                                        "sent_a": claims[i]["text"],
                                        "sent_b": claims[target_idx]["text"],
                                        "pub_a": claims[i]["publisher_id"],
                                        "pub_b": claims[target_idx]["publisher_id"],
                                        "nums_a": list(nums_a),
                                        "nums_b": list(nums_b)
                                    })
            except Exception as e:
                logger.error(f"Claim semantic embedding calculations failed: {e}")

        # Compute scores
        story.verification_score = verified_claims_count / max(1, total_claims_checked)

        # ── Step 2: Credibility Index calculation ──
        # credibility_score = w1*Diversity + w2*Authority + w3*Agreement - w4*Contradiction
        diversity = story.publisher_diversity / max(1, story.article_count)

        # Calculate authority averages
        pub_scores = []
        evidence_data = []
        for art in articles:
            stmt_p = select(Publisher).where(Publisher.id == art.publisher_id)
            res_p = await self.db.execute(stmt_p)
            pub = res_p.scalar_one_or_none()
            cred = float(pub.credibility_score) if pub else 0.90
            pub_scores.append(cred)
            evidence_data.append({
                "publisher_id": art.publisher_id,
                "credibility": cred,
                "article_title": art.title,
                "article_hash": art.article_hash
            })

        avg_authority = sum(pub_scores) / max(1, len(pub_scores))
        agreement_ratio = verified_claims_count / max(1, total_claims_checked)
        contradiction_ratio = contradiction_count / max(1, total_claims_checked)

        cred_score = (0.3 * diversity) + (0.4 * avg_authority) + (0.3 * agreement_ratio) - (0.2 * contradiction_ratio)
        story.credibility_score = max(0.0, min(1.0, cred_score))

        # Evidence registries
        story.evidence = evidence_data

        # Calculate structured verification details
        trusted_publishers = sum(1 for score in pub_scores if score >= 0.85)
        conflicting_publishers = {c["pub_a"] for c in conflicts_list}.union({c["pub_b"] for c in conflicts_list})
        conflicting_articles_count = len(conflicting_publishers)

        story.verification_metadata = {
            "agreement_score": round(agreement_ratio, 2),
            "publisher_diversity": story.publisher_diversity,
            "trusted_publishers": trusted_publishers,
            "supporting_articles": story.article_count,
            "conflicting_articles": conflicting_articles_count,
            "semantic_confidence": round(float(story.confidence_score) if story.confidence_score is not None else 1.0, 2)
        }

        story.formation_evidence = {
            "similarity_threshold": 0.82,
            "supporting_publishers_count": story.publisher_diversity,
            "has_conflicts": story.has_conflicts,
            "conflicts": conflicts_list[:5]
        }

        # ── Step 3: Timelines & Graph Relationships ──
        await self.generate_timeline(story)
        await self.update_graph_relationships(story)

        await self.db.commit()
        logger.info(f"Verified story {story.id} successfully: verification={story.verification_score:.2f}, credibility={story.credibility_score:.2f}")

    async def generate_timeline(self, story: Story) -> None:
        """
        Chronologically orders and generates timeline events for the story.
        Groups articles published within 6-hour windows into unified milestones.
        """
        # Delete existing timeline entries to keep it idempotent
        await self.db.execute(delete(StoryTimeline).where(StoryTimeline.story_id == story.id))

        sorted_articles = list(story.articles)
        sorted_articles.sort(key=lambda a: a.published_at if a.published_at else datetime.now(timezone.utc))

        if not sorted_articles:
            return

        # Group articles into 6-hour windows
        windows = []
        current_window = []
        window_start_time = None

        for art in sorted_articles:
            art_time = art.published_at if art.published_at else datetime.now(timezone.utc)
            if window_start_time is None:
                window_start_time = art_time
                current_window.append(art)
            else:
                gap = (art_time - window_start_time).total_seconds() / 3600.0
                if gap <= 6.0:
                    current_window.append(art)
                else:
                    windows.append(current_window)
                    current_window = [art]
                    window_start_time = art_time
        if current_window:
            windows.append(current_window)

        # Generate a milestone timeline event for each window
        for idx, win in enumerate(windows):
            first_art = win[0]

            # Count supporting articles and publishers in this window
            supporting_articles_count = len(win)
            supporting_publishers_count = len({art.publisher_id for art in win})

            # Find representative quality score
            qualities = [float(art.quality_score) for art in win if art.quality_score is not None]
            avg_quality = sum(qualities) / len(qualities) if qualities else 0.85

            # Confidence score formula
            confidence = min(1.0, avg_quality + 0.05 * (supporting_publishers_count - 1))

            # Determine event type
            if idx == 0:
                event_type = "first_appearance"
            else:
                has_correction = False
                for art in win:
                    body_lower = (art.body_text or "").lower()
                    if "correction" in body_lower or "clarification" in body_lower or "amend" in body_lower:
                        has_correction = True
                        break

                if has_correction:
                    event_type = "correction"
                elif story.publisher_diversity > 3 and idx == len(windows) - 1:
                    event_type = "major_development"
                else:
                    event_type = "update"

            milestone = StoryTimeline(
                id=uuid.uuid4(),
                story_id=story.id,
                event_timestamp=first_art.published_at if first_art.published_at else datetime.now(timezone.utc),
                headline=first_art.title[:255] if first_art.title else "Story milestone update",
                description=first_art.body_text[:250] + "..." if first_art.body_text else "Details pending.",
                event_type=event_type,
                confidence_score=round(confidence, 2),
                supporting_articles=supporting_articles_count,
                supporting_publishers=supporting_publishers_count
            )
            self.db.add(milestone)

        await self.db.commit()

    async def update_graph_relationships(self, story: Story) -> None:
        """
        Computes similarity between story centroids in Qdrant and establishes
        directed graph relationships in parent/child mappings.
        """
        if not story.centroid_vector_id:
            return

        try:
            # Fetch centroid vector
            points = self.vector_store.client.retrieve(
                collection_name="stories",
                ids=[str(story.id)],
                with_vectors=True
            )
            if not points or not points[0].vector:
                return
            story_vec = points[0].vector
        except Exception as qe:
            logger.error(f"Failed to load story centroid for relation check: {qe}")
            return

        try:
            # Query Qdrant for similar stories
            matches = self.vector_store.search_similar("stories", story_vec, top_k=10)
            for m in matches:
                match_id = uuid.UUID(str(m["id"]))
                if match_id == story.id:
                    continue

                score = m["score"]
                if score >= 0.50:
                    # Query metadata
                    stmt = select(Story).where(Story.id == match_id)
                    res = await self.db.execute(stmt)
                    other_story = res.scalar_one_or_none()
                    if not other_story:
                        continue

                    t1 = story.first_reported_at or story.created_at
                    t2 = other_story.first_reported_at or other_story.created_at

                    # Older story is parent, newer story is child
                    if t1 < t2:
                        parent_id = story.id
                        child_id = other_story.id
                        delta = (t2 - t1).total_seconds() / 3600.0
                    else:
                        parent_id = other_story.id
                        child_id = story.id
                        delta = (t1 - t2).total_seconds() / 3600.0

                    rel_type = "FOLLOW_UP" if delta > 24.0 else "RELATED"

                    # Verify connection if it already exists
                    stmt_r = (
                        select(StoryRelation)
                        .where(
                            StoryRelation.parent_story_id == parent_id,
                            StoryRelation.child_story_id == child_id
                        )
                    )
                    res_r = await self.db.execute(stmt_r)
                    existing = res_r.scalar_one_or_none()

                    if not existing:
                        relation = StoryRelation(
                            parent_story_id=parent_id,
                            child_story_id=child_id,
                            relation_type=rel_type
                        )
                        self.db.add(relation)
        except Exception as e:
            logger.error(f"Failed to update story graph relations: {e}")

    def _extract_key_words(self, text: str) -> set:
        """Helper to extract noun/proper-noun lemmas for Jaccard comparisons."""
        if not self.nlp:
            # Fallback simple split
            return set(re.findall(r"\b\w{4,}\b", text.lower()))

        doc = self.nlp(text)
        words = set()
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] or token.ent_type_ in ["ORG", "PERSON", "GPE"]:
                text_clean = token.text.lower().strip()
                if text_clean and re.match(r"^\w+$", text_clean):
                    words.add(text_clean)
        return words

    def _extract_numbers(self, text: str) -> set:
        """Regex to isolate numerical metrics, ignoring years (4 digits)."""
        nums = set(re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", text))
        return {n for n in nums if not (n.isdigit() and len(n) == 4)}
