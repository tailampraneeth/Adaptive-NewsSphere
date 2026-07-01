import asyncio
from app.core.logging import logger
from app.database.connection import AsyncSessionLocal
from app.services.ingestion import IngestionService

# Default feed list config
DEFAULT_FEEDS = {
    "bbc": {
        "name": "BBC News Technology",
        "feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "url": "https://www.bbc.com"
    },
    "reuters": {
        "name": "Reuters Business",
        "feed_url": "https://feeds.reuters.com/reuters/businessNews",
        "url": "https://www.reuters.com"
    }
}

async def run_ingestion():
    """Main execution loop running the feed parser ingestion tasks."""
    logger.info("Initializing background news ingestion sequence...")

    async with AsyncSessionLocal() as session:
        service = IngestionService(session)

        for pub_id, info in DEFAULT_FEEDS.items():
            try:
                # Ensure publisher exists in relational metadata registry
                await service.ensure_publisher(
                    pub_id=pub_id,
                    name=info["name"],
                    url=info["url"]
                )

                # Fetch and ingest articles
                stats = await service.ingest_feed(
                    publisher_id=pub_id,
                    feed_url=info["feed_url"]
                )

                logger.info(
                    f"Feed ingestion stats for '{pub_id}': "
                    f"Attempted: {stats['attempted']}, "
                    f"Inserted: {stats['inserted']}, "
                    f"Skipped Duplicates: {stats['skipped_duplicate']}, "
                    f"Errors: {stats['errors']}"
                )

            except Exception as e:
                logger.error(f"Error during ingestion cycle for '{pub_id}': {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_ingestion())
