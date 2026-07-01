"""
IngestionService — RSS feed ingestion and parsing engine.

Fetches articles from registered publishers' RSS feeds, runs HTML stripping
and normalization, checks for exact URL and content hash duplicates,
calculates article quality scores, and records feed health metrics.

Features:
  - Quality score calculation based on metadata completeness, length, and credibility.
  - Persistent publisher feed health updates (moving averages of latency, success/failure rate, duplicate count).
  - Version history / updated articles detection: if URL exists but hash changes,
    the article is imported with a modified URL fragment and marked as UPDATED_ARTICLE.
"""
import logging
from datetime import datetime, timezone
import time
from typing import Dict, Optional
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import Article, Publisher
from app.utils.text_cleaner import clean_html, generate_article_hashes

logger = logging.getLogger("adaptive-newssphere.ingestion")


def calculate_article_quality(
    title: str,
    body_text: str,
    author: Optional[str],
    image_url: Optional[str],
    pub_credibility: float,
) -> float:
    """
    Computes a baseline quality score ∈ [0.0, 1.0] for the article.
    
    Weights:
      - Body length (word count): up to 0.30
      - Author field present: 0.15
      - Image URL present: 0.15
      - Title length sanity check: 0.15
      - Publisher credibility: up to 0.25
    """
    score = 0.0

    # 1. Body length (word count) - up to 0.30
    words = len(body_text.split()) if body_text else 0
    if words > 300:
        score += 0.30
    elif words > 100:
        score += 0.20
    elif words > 0:
        score += 0.10

    # 2. Metadata completeness - up to 0.30
    if author and len(author.strip()) > 0:
        score += 0.15
    if image_url and len(image_url.strip()) > 0:
        score += 0.15

    # 3. Title quality length - up to 0.15
    title_len = len(title) if title else 0
    if 15 < title_len < 150:
        score += 0.15

    # 4. Publisher credibility - up to 0.25
    score += pub_credibility * 0.25

    return round(min(1.0, score), 2)


class IngestionService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def ensure_publisher(self, pub_id: str, name: str, url: str) -> Publisher:
        """Checks if a publisher exists in PostgreSQL registry, creating it if missing."""
        result = await self.db.execute(select(Publisher).filter_by(id=pub_id))
        publisher = result.scalar_one_or_none()

        if not publisher:
            logger.info(f"Registering new publisher: {name} ({pub_id})")
            publisher = Publisher(
                id=pub_id,
                name=name,
                base_url=url,
                credibility_score=1.00,
                bias_rating="center",
                successful_fetches=0,
                failed_fetches=0,
                avg_latency_ms=0.0,
                articles_per_fetch=0.0,
                duplicate_percentage=0.0,
            )
            self.db.add(publisher)
            await self.db.commit()
            await self.db.refresh(publisher)

        return publisher

    async def ingest_feed(self, publisher_id: str, feed_url: str) -> Dict[str, int]:
        """Parses articles from an RSS feed url and saves non-duplicate records to PostgreSQL."""
        logger.info(f"Parsing RSS Feed for publisher '{publisher_id}': {feed_url}")

        # Fetch publisher credibility score
        pub_res = await self.db.execute(select(Publisher).filter_by(id=publisher_id))
        publisher = pub_res.scalar_one_or_none()
        pub_cred = float(publisher.credibility_score) if publisher else 1.00

        t0 = time.perf_counter()
        stats = {"attempted": 0, "inserted": 0, "skipped_duplicate": 0, "errors": 0}

        try:
            # Parse XML feed content
            feed = feedparser.parse(feed_url)
            latency_ms = (time.perf_counter() - t0) * 1000

            # Check for parsing errors
            if hasattr(feed, "bozo") and feed.bozo and isinstance(feed.bozo_exception, Exception):
                raise feed.bozo_exception
        except Exception as e:
            logger.error(f"Failed to fetch/parse RSS Feed for publisher '{publisher_id}': {e}")
            if publisher:
                publisher.failed_fetches = (publisher.failed_fetches or 0) + 1
                await self.db.commit()
            raise e

        # Process feed entries
        for entry in feed.entries:
            stats["attempted"] += 1
            try:
                url = entry.get("link")
                if not url:
                    logger.warning("Skipping entry missing canonical link URL.")
                    stats["errors"] += 1
                    continue

                # Extract title and body text
                title = entry.get("title", "")
                body_text = ""
                content_list = entry.get("content")
                if content_list and len(content_list) > 0:
                    body_text = content_list[0].get("value", "")
                elif "summary" in entry:
                    body_text = entry.get("summary", "")
                else:
                    body_text = entry.get("description", "")

                cleaned_body = clean_html(body_text)
                cleaned_title = clean_html(title)

                if not cleaned_body:
                    logger.warning(f"Skipping article '{title}' with empty text body.")
                    stats["errors"] += 1
                    continue

                # Calculate content and article hashes for deduplication
                content_hash, article_hash = generate_article_hashes(cleaned_title, cleaned_body)

                duplicate_type = None

                # Check if URL already exists in database
                url_check = await self.db.execute(select(Article).filter_by(source_url=url))
                existing_article = url_check.scalar_one_or_none()
                if existing_article:
                    # If same URL but content hash changed -> UPDATED_ARTICLE version
                    if existing_article.article_hash != article_hash:
                        url = f"{url}#updated-{int(time.time())}"
                        duplicate_type = "UPDATED_ARTICLE"
                    else:
                        stats["skipped_duplicate"] += 1
                        continue

                # Check if article hash already exists (republished elsewhere)
                hash_check = await self.db.execute(select(Article).filter_by(article_hash=article_hash))
                if hash_check.scalar_one_or_none():
                    stats["skipped_duplicate"] += 1
                    continue

                # Parse publication time (convert feed struct_time to datetime object)
                published_time = datetime.now(timezone.utc)
                published_parsed = entry.get("published_parsed")
                updated_parsed = entry.get("updated_parsed")
                if published_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)
                elif updated_parsed:
                    published_time = datetime.fromtimestamp(time.mktime(updated_parsed), tz=timezone.utc)

                author = entry.get("author")

                # Extract image URL
                image_url = None
                media_content = entry.get("media_content")
                if media_content and len(media_content) > 0:
                    image_url = media_content[0].get("url")
                elif "links" in entry:
                    for link in entry.get("links", []):
                        if "image" in link.get("type", ""):
                            image_url = link.get("href")
                            break

                tags = [tag.term for tag in entry.get("tags", []) if hasattr(tag, "term")]
                category = entry.get("category") or (tags[0] if tags else None)

                # Initialize base article model
                article = Article(
                    publisher_id=publisher_id,
                    title=cleaned_title,
                    body_text=cleaned_body,
                    author=author,
                    source_url=url,
                    published_at=published_time,
                    language="en",
                    category=category,
                    image_url=image_url,
                    tags=tags,
                    content_hash=content_hash,
                    article_hash=article_hash,
                    duplicate_type=duplicate_type,
                )

                # Compute baseline quality score
                article.quality_score = calculate_article_quality(
                    cleaned_title, cleaned_body, author, image_url, pub_cred
                )

                self.db.add(article)
                stats["inserted"] += 1

            except Exception as e:
                logger.error(f"Failed to process RSS entry: {e}", exc_info=True)
                stats["errors"] += 1

        # Commit batch transactions and update publisher health metrics
        if publisher:
            publisher.successful_fetches = (publisher.successful_fetches or 0) + 1
            prev_count = max(0, publisher.successful_fetches - 1)

            # Compute running moving average of latency
            prev_avg_latency = publisher.avg_latency_ms or 0.0
            publisher.avg_latency_ms = ((prev_avg_latency * prev_count) + latency_ms) / publisher.successful_fetches

            # Compute running moving average of articles count per fetch
            prev_avg_articles = publisher.articles_per_fetch or 0.0
            publisher.articles_per_fetch = ((prev_avg_articles * prev_count) + stats["attempted"]) / publisher.successful_fetches

            # Compute running moving average of duplicate percentage
            duplicate_pct = (stats["skipped_duplicate"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0.0
            prev_avg_dup = publisher.duplicate_percentage or 0.0
            publisher.duplicate_percentage = ((prev_avg_dup * prev_count) + duplicate_pct) / publisher.successful_fetches

            publisher.last_fetched_at = datetime.now(timezone.utc)

        await self.db.commit()
        logger.info(f"Ingestion complete for '{publisher_id}': inserted={stats['inserted']}, skipped={stats['skipped_duplicate']}, errors={stats['errors']}.")

        return stats
