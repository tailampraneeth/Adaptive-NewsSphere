import logging
from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import Article, Publisher
from app.utils.text_cleaner import clean_html, generate_article_hashes

logger = logging.getLogger("adaptive-newssphere.ingestion")

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
                bias_rating="center"
            )
            self.db.add(publisher)
            await self.db.commit()
            await self.db.refresh(publisher)
            
        return publisher

    async def ingest_feed(self, publisher_id: str, feed_url: str) -> Dict[str, int]:
        """Parses articles from an RSS feed url and saves non-duplicate records to PostgreSQL."""
        logger.info(f"Parsing RSS Feed for publisher '{publisher_id}': {feed_url}")
        
        # Parse XML feed content
        feed = feedparser.parse(feed_url)
        
        stats = {"attempted": 0, "inserted": 0, "skipped_duplicate": 0, "errors": 0}
        
        for entry in feed.entries:
            stats["attempted"] += 1
            try:
                # Extract URL and check if it already exists
                url = entry.get("link")
                if not url:
                    logger.warning("Skipping entry missing canonical link URL.")
                    stats["errors"] += 1
                    continue

                # Check if URL already exists in database
                url_check = await self.db.execute(select(Article).filter_by(source_url=url))
                if url_check.scalar_one_or_none():
                    stats["skipped_duplicate"] += 1
                    continue

                # Extract title and body text
                title = entry.get("title", "")
                
                # Retrieve body from summary or content blocks
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

                # Check if article hash already exists
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

                # Extract optional fields
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

                # Instaniate model
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
                    article_hash=article_hash
                )
                
                self.db.add(article)
                stats["inserted"] += 1
                
            except Exception as e:
                logger.error(f"Failed to process RSS entry: {e}", exc_info=True)
                stats["errors"] += 1

        # Commit batch transactions
        if stats["inserted"] > 0:
            await self.db.commit()
            logger.info(f"Batch insert completed. Added {stats['inserted']} new articles for '{publisher_id}'.")
            
        return stats
