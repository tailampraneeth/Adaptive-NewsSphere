import logging
import time
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.database.models.story import Story
from app.utils.text_cleaner import clean_html, generate_article_hashes
from app.services.category_classifier import CategoryClassifierService
from app.services.story_grouper import StoryGrouperService
from app.services.summarizer import StorySummarizerService

logger = logging.getLogger("heimdall.ingestion")


async def resolve_canonical_url(url: str) -> str:
    """Follows redirects using HTTP HEAD request to determine the final canonical URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(url, follow_redirects=True)
            return str(resp.url)
    except Exception as e:
        logger.debug(f"Failed to resolve canonical URL for {url}: {e}")
        return url


class IngestionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.classifier = CategoryClassifierService()
        self.grouper = StoryGrouperService()
        self.summarizer = StorySummarizerService()

    async def ensure_publisher(self, pub_id: str, name: str, url: str, rss_url: str) -> Publisher:
        """Ensures a publisher exists in the database registry."""
        result = await self.db.execute(select(Publisher).filter_by(id=pub_id))
        publisher = result.scalar_one_or_none()

        if not publisher:
            logger.info(f"Registering new publisher: {name} ({pub_id})")
            publisher = Publisher(
                id=pub_id,
                name=name,
                base_url=url,
                rss_url=rss_url,
                credibility_score=1.00,
                successful_fetches=0,
                failed_fetches=0,
            )
            self.db.add(publisher)
            await self.db.commit()
            await self.db.refresh(publisher)

        return publisher

    async def ingest_feed(self, publisher_id: str, feed_url: str) -> Dict[str, int]:
        """Parses articles from an RSS feed and saves them, clustering and summarizing dynamically."""
        logger.info(f"Ingesting RSS Feed for publisher '{publisher_id}': {feed_url}")

        pub_res = await self.db.execute(select(Publisher).filter_by(id=publisher_id))
        publisher = pub_res.scalar_one_or_none()

        stats = {"attempted": 0, "inserted": 0, "skipped_duplicate": 0, "errors": 0}

        try:
            feed = feedparser.parse(feed_url)
            if hasattr(feed, "bozo") and feed.bozo and isinstance(feed.bozo_exception, Exception):
                raise feed.bozo_exception
        except Exception as e:
            logger.error(f"Failed to parse RSS Feed for '{publisher_id}': {e}")
            if publisher:
                publisher.failed_fetches = (publisher.failed_fetches or 0) + 1
                await self.db.commit()
            raise e

        # Read recent stories (last 12 hours) for clustering
        # We eagerly load articles to avoid N+1 queries during Jaccard calculation
        story_stmt = (
            select(Story)
            .options(selectinload(Story.articles))
            .where(Story.status == "ACTIVE")
            .where(Story.last_updated_at > datetime.now(timezone.utc) - select(func.interval('12 hours'))) # Wait, SQLAlchemy interval support varies. Let's do datetime subtraction in Python.
        )
        # Let's compute the Python boundary datetime to be database independent
        boundary = datetime.now(timezone.utc) - select(func.interval('12 hours')) # wait, let's just pass python datetime
        # Actually, python datetime is database independent and safer!
        from datetime import timedelta
        boundary_time = datetime.now(timezone.utc) - timedelta(hours=12)

        story_stmt = (
            select(Story)
            .options(selectinload(Story.articles))
            .where(Story.status == "ACTIVE")
            .where(Story.last_updated_at >= boundary_time)
        )
        recent_stories_res = await self.db.execute(story_stmt)
        recent_stories = list(recent_stories_res.scalars().all())

        for entry in feed.entries:
            stats["attempted"] += 1
            try:
                raw_url = entry.get("link")
                if not raw_url:
                    stats["errors"] += 1
                    continue

                title = clean_html(entry.get("title", ""))
                body_text = ""
                content_list = entry.get("content")
                if content_list:
                    body_text = content_list[0].get("value", "")
                elif "summary" in entry:
                    body_text = entry.get("summary", "")
                else:
                    body_text = entry.get("description", "")

                cleaned_body = clean_html(body_text)
                if not title or not cleaned_body:
                    stats["errors"] += 1
                    continue

                content_hash, article_hash = generate_article_hashes(title, cleaned_body)

                # Check duplicates by hash (republished elsewhere or exact match)
                hash_check = await self.db.execute(select(Article).filter_by(article_hash=article_hash))
                if hash_check.scalar_one_or_none():
                    stats["skipped_duplicate"] += 1
                    continue

                # Resolve canonical URL
                canonical_url = await resolve_canonical_url(raw_url)

                # Check duplicate by canonical URL
                url_check = await self.db.execute(select(Article).filter_by(canonical_url=canonical_url))
                if url_check.scalar_one_or_none():
                    stats["skipped_duplicate"] += 1
                    continue

                # Parse publication time
                published_time = datetime.now(timezone.utc)
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)

                # NLP attributes fallback
                tags = [tag.term for tag in entry.get("tags", []) if hasattr(tag, "term")]
                category_raw = entry.get("category") or (tags[0] if tags else None)

                predicted_cat, conf = await self.classifier.classify(title, cleaned_body)

                # Compute reading time (approx 200 words per minute)
                words = len(cleaned_body.split())
                reading_time = max(1, words // 200)

                # Construct Article object
                article = Article(
                    publisher_id=publisher_id,
                    title=title,
                    body_text=cleaned_body,
                    author=entry.get("author"),
                    source_url=raw_url,
                    canonical_url=canonical_url,
                    published_at=published_time,
                    language="en",
                    category=category_raw,
                    predicted_category=predicted_cat,
                    category_confidence=conf,
                    image_url=entry.get("media_content", [{}])[0].get("url") if entry.get("media_content") else None,
                    tags=tags,
                    content_hash=content_hash,
                    article_hash=article_hash,
                    reading_time=reading_time,
                    subtitle=entry.get("subtitle"),
                    keywords=tags[:5], # fallback keywords
                )
                self.db.add(article)
                await self.db.flush() # Populate ID

                # ── Story Clustering ──
                matched_story, is_same_pub_update = self.grouper.cluster_article(article, recent_stories)

                if matched_story:
                    logger.info(f"Article '{title[:30]}' joined existing Story '{matched_story.title[:30]}'")
                    article.story_id = matched_story.id
                    matched_story.last_updated_at = max(matched_story.last_updated_at, published_time)
                    matched_story.article_count += 1
                    if not is_same_pub_update:
                        matched_story.publisher_diversity += 1
                else:
                    logger.info(f"Article '{title[:30]}' created a new Story")
                    new_story = Story(
                        title=article.title,
                        summary=article.body_text[:300] + "...",
                        status="ACTIVE",
                        article_count=1,
                        publisher_diversity=1,
                        first_reported_at=published_time,
                        last_updated_at=published_time,
                        predicted_category=predicted_cat,
                        representative_article_id=article.id
                    )
                    self.db.add(new_story)
                    await self.db.flush()
                    article.story_id = new_story.id
                    matched_story = new_story
                    recent_stories.append(new_story)

                stats["inserted"] += 1

            except Exception as e:
                logger.error(f"Failed to process RSS entry: {e}", exc_info=True)
                stats["errors"] += 1

        if publisher:
            publisher.successful_fetches = (publisher.successful_fetches or 0) + 1
            publisher.last_fetched_at = datetime.now(timezone.utc)

        await self.db.commit()
        logger.info(f"Ingestion done for '{publisher_id}': {stats}")
        return stats
