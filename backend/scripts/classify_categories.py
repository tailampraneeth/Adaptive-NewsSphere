"""
classify_categories.py — Batch article category classification.

Fetches articles with missing or unclassified categories from the database
and runs them through CategoryClassifierService. Writes predicted_category
and category_confidence back to the database.

Can be run incrementally:
  - Without arguments: processes only articles with predicted_category = NULL
  - With --force: re-classifies ALL articles (overwrites existing predictions)

Usage:
  python scripts/classify_categories.py
  python scripts/classify_categories.py --force

Exit codes:
  0 — success
  1 — no articles to process or error
"""
import asyncio
import argparse
import os
import sys
import time

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.article import Article
from app.services.category_classifier import CategoryClassifierService
from app.services.vector_store import VectorStoreService


async def run_classification(force: bool = False) -> None:
    db_url = settings.get_database_url()

    print("=" * 60)
    print("    ADAPTIVE NEWSSPHERE: CATEGORY CLASSIFICATION")
    print("=" * 60)
    print(f"  Mode: {'FORCE (re-classify all)' if force else 'INCREMENTAL (NULL only)'}")
    print()

    # Initialize services
    print("[*] Loading CategoryClassifierService and VectorStoreService...")
    classifier = CategoryClassifierService()
    vector_store = VectorStoreService()

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        # Fetch target articles
        if force:
            result = await session.execute(select(Article))
        else:
            result = await session.execute(
                select(Article).where(Article.predicted_category.is_(None))
            )

        articles = result.scalars().all()
        total = len(articles)

        if total == 0:
            print("[*] No articles require classification. All done!")
            await engine.dispose()
            return

        print(f"[*] Found {total} articles to classify.")
        print()

        t0 = time.time()
        processed = 0
        confidence_buckets = {"high (>= 0.70)": 0, "medium (0.45-0.69)": 0, "low (keyword < 0.45)": 0}
        category_counts: dict = {}

        for article in articles:
            try:
                category, confidence = await classifier.classify(
                    article.title, article.body_text, db=session, vector_store=vector_store
                )
                article.predicted_category = category
                article.category_confidence = confidence

                # Track stats
                category_counts[category] = category_counts.get(category, 0) + 1
                if confidence >= 0.70:
                    confidence_buckets["high (>= 0.70)"] += 1
                elif confidence >= 0.45:
                    confidence_buckets["medium (0.45-0.69)"] += 1
                else:
                    confidence_buckets["low (keyword < 0.45)"] += 1

                processed += 1
                if processed % 50 == 0:
                    print(f"  [+] Classified {processed}/{total}...")

            except Exception as e:
                print(f"  [!] Error on article {article.id}: {e}")

        await session.commit()
        duration = time.time() - t0

        print()
        print("=" * 60)
        print("              CLASSIFICATION RESULTS")
        print("=" * 60)
        print(f"  Articles Processed    : {processed}")
        print(f"  Time Elapsed          : {duration:.2f}s")
        print(f"  Avg. Time Per Article : {duration / max(processed, 1) * 1000:.1f}ms")
        print()
        print("  Category Distribution:")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            bar = "#" * (count * 20 // max(category_counts.values(), default=1))
            print(f"    {cat:<15} {count:>4} {bar}")
        print()
        print("  Confidence Distribution:")
        for label, count in confidence_buckets.items():
            print(f"    {label}: {count}")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify article categories")
    parser.add_argument("--force", action="store_true",
                        help="Re-classify all articles (not just NULL)")
    args = parser.parse_args()
    asyncio.run(run_classification(force=args.force))
