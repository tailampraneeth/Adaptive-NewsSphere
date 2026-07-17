import logging
import re
import uuid
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

logger = logging.getLogger("heimdall.story_verification")


class StoryVerificationService:
    """
    Implements deterministic, CPU-friendly Story Intelligence & Verification.
    Does NOT use external embedding APIs or local transformer models.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            logger.warning("spaCy model en_core_web_sm not loaded. Falling back to basic sentence splitting.")
            self.nlp = None

    async def verify_story(self, story_id: uuid.UUID) -> None:
        """Performs full verification, credibility scoring, evidence compiling, and timeline generation."""
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

        pub_times = [a.published_at for a in articles if a.published_at]
        if pub_times:
            story.first_reported_at = min(pub_times)
            story.last_updated_at = max(pub_times)

        # Base case: single-source stories
        if len(articles) <= 1:
            story.verification_score = 1.0
            story.has_conflicts = False
            art = articles[0]
            stmt_p = select(Publisher).where(Publisher.id == art.publisher_id)
            res_p = await self.db.execute(stmt_p)
            pub = res_p.scalar_one_or_none()
            story.credibility_score = float(pub.credibility_score) if pub else 0.90

            story.evidence = [{
                "publisher_id": art.publisher_id,
                "credibility": float(pub.credibility_score) if pub else 0.90,
                "article_title": art.title,
                "article_hash": art.article_hash
            }]
            story.verification_metadata = {
                "agreement_score": 1.0,
                "publisher_diversity": 1,
                "trusted_publishers": 1 if (pub and pub.credibility_score >= 0.85) else 0,
                "supporting_articles": 1,
                "conflicting_articles": 0,
                "semantic_confidence": 1.0
            }
            await self.generate_timeline(story)
            await self.update_graph_relationships(story)
            await self.db.commit()
            return

        # Multi-source comparison using sentences & Jaccard overlap
        claims = []
        for art in articles:
            body = art.body_text or ""
            if self.nlp:
                doc = self.nlp(body)
                sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 30]
            else:
                sentences = [s.strip() for s in body.split(".") if len(s.strip()) > 30]

            for s in sentences[:10]:  # limit sentences to optimize execution
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

        for i, claim_a in enumerate(claims):
            total_claims_checked += 1
            found_match = False
            words_a = self._extract_key_words(claim_a["text"])

            for j, claim_b in enumerate(claims):
                if claim_a["publisher_id"] == claim_b["publisher_id"]:
                    continue

                words_b = self._extract_key_words(claim_b["text"])
                union = words_a.union(words_b)
                intersection = words_a.intersection(words_b)
                jaccard = len(intersection) / len(union) if union else 0.0

                # Jaccard overlap threshold for statement agreement
                if jaccard >= 0.50:
                    found_match = True
                    agreement_count += 1
                    break

            if found_match:
                verified_claims_count += 1
            else:
                # If no match, check if they reference similar topics but disagree on metrics/numbers
                for j, claim_b in enumerate(claims):
                    if claim_a["publisher_id"] == claim_b["publisher_id"]:
                        continue

                    words_b = self._extract_key_words(claim_b["text"])
                    union = words_a.union(words_b)
                    intersection = words_a.intersection(words_b)
                    jaccard = len(intersection) / len(union) if union else 0.0

                    if 0.25 <= jaccard < 0.50:
                        nums_a = self._extract_numbers(claim_a["text"])
                        nums_b = self._extract_numbers(claim_b["text"])
                        if nums_a and nums_b and nums_a != nums_b:
                            contradiction_count += 1
                            story.has_conflicts = True
                            conflicts_list.append({
                                "sent_a": claim_a["text"],
                                "sent_b": claim_b["text"],
                                "pub_a": claim_a["publisher_id"],
                                "pub_b": claim_b["publisher_id"],
                                "nums_a": list(nums_a),
                                "nums_b": list(nums_b)
                            })

        # Calculate scores
        story.verification_score = round(verified_claims_count / max(1, total_claims_checked), 2)
        diversity = story.publisher_diversity / max(1, story.article_count)

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
        story.credibility_score = round(max(0.0, min(1.0, cred_score)), 2)
        story.evidence = evidence_data

        trusted_publishers = sum(1 for score in pub_scores if score >= 0.85)
        conflicting_publishers = {c["pub_a"] for c in conflicts_list}.union({c["pub_b"] for c in conflicts_list})

        story.verification_metadata = {
            "agreement_score": round(agreement_ratio, 2),
            "publisher_diversity": story.publisher_diversity,
            "trusted_publishers": trusted_publishers,
            "supporting_articles": story.article_count,
            "conflicting_articles": len(conflicting_publishers),
            "semantic_confidence": 1.0
        }

        await self.generate_timeline(story)
        await self.update_graph_relationships(story)
        await self.db.commit()

    async def generate_timeline(self, story: Story) -> None:
        """Groups story articles into chronological 6-hour windows and saves them to timeline."""
        await self.db.execute(delete(StoryTimeline).where(StoryTimeline.story_id == story.id))

        sorted_articles = sorted(story.articles, key=lambda a: a.published_at or datetime.now(timezone.utc))
        if not sorted_articles:
            return

        windows = []
        current_window = []
        window_start_time = None

        for art in sorted_articles:
            art_time = art.published_at or datetime.now(timezone.utc)
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

        for idx, win in enumerate(windows):
            first_art = win[0]
            supporting_articles_count = len(win)
            supporting_publishers_count = len({art.publisher_id for art in win})

            confidence = min(1.0, 0.80 + 0.05 * (supporting_publishers_count - 1))

            if idx == 0:
                event_type = "first_appearance"
            else:
                has_correction = any("correction" in (a.body_text or "").lower() for a in win)
                if has_correction:
                    event_type = "correction"
                elif story.publisher_diversity > 3 and idx == len(windows) - 1:
                    event_type = "major_development"
                else:
                    event_type = "update"

            milestone = StoryTimeline(
                id=uuid.uuid4(),
                story_id=story.id,
                event_timestamp=first_art.published_at or datetime.now(timezone.utc),
                headline=first_art.title[:255],
                description=(first_art.body_text[:250] + "...") if first_art.body_text else "Details pending.",
                event_type=event_type,
                confidence_score=round(confidence, 2),
                supporting_articles=supporting_articles_count,
                supporting_publishers=supporting_publishers_count
            )
            self.db.add(milestone)
        await self.db.commit()

    async def update_graph_relationships(self, story: Story) -> None:
        """Establishes RELATED and FOLLOW_UP story links using matching keywords & timelines."""
        t1 = story.first_reported_at or story.created_at
        boundary_time = t1 - select(func.interval('48 hours')) # wait, let's use timedelta for db-independence
        from datetime import timedelta
        min_time = t1 - timedelta(hours=48)
        max_time = t1 + timedelta(hours=48)

        stmt = (
            select(Story)
            .where(Story.predicted_category == story.predicted_category)
            .where(Story.id != story.id)
            .where(Story.first_reported_at >= min_time)
            .where(Story.first_reported_at <= max_time)
        )
        res = await self.db.execute(stmt)
        matching_stories = res.scalars().all()

        story_keywords = set()
        for art in story.articles:
            if art.keywords:
                story_keywords.update(art.keywords)

        for other in matching_stories:
            other_keywords = set()
            for art in other.articles:
                if art.keywords:
                    other_keywords.update(art.keywords)

            overlap = len(story_keywords & other_keywords)
            if overlap >= 2:
                t2 = other.first_reported_at or other.created_at
                if t1 < t2:
                    parent_id = story.id
                    child_id = other.id
                    delta = (t2 - t1).total_seconds() / 3600.0
                else:
                    parent_id = other.id
                    child_id = story.id
                    delta = (t1 - t2).total_seconds() / 3600.0

                rel_type = "FOLLOW_UP" if delta > 24.0 else "RELATED"

                stmt_r = (
                    select(StoryRelation)
                    .where(
                        StoryRelation.parent_story_id == parent_id,
                        StoryRelation.child_story_id == child_id
                    )
                )
                res_r = await self.db.execute(stmt_r)
                if not res_r.scalar_one_or_none():
                    relation = StoryRelation(
                        parent_story_id=parent_id,
                        child_story_id=child_id,
                        relation_type=rel_type
                    )
                    self.db.add(relation)

    def _extract_key_words(self, text: str) -> set:
        if not self.nlp:
            return set(re.findall(r"\b\w{4,}\b", text.lower()))
        doc = self.nlp(text)
        words = set()
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] or token.ent_type_ in ["ORG", "PERSON", "GPE"]:
                clean = token.text.lower().strip()
                if clean and re.match(r"^\w+$", clean):
                    words.add(clean)
        return words

    def _extract_numbers(self, text: str) -> set:
        nums = set(re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", text))
        return {n for n in nums if not (n.isdigit() and len(n) == 4)}
