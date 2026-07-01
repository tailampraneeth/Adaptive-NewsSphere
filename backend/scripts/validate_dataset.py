import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.article import Article
from app.utils.data_validator import DataValidator

async def validate_dataset():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: DATASET QUALITY VALIDATOR")
    print("=" * 60)
    
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Fetch all articles in the database
        result = await session.execute(select(Article))
        articles = result.scalars().all()
        
        total_articles = len(articles)
        print(f"[*] Validating {total_articles} articles in local PostgreSQL...")
        
        stats = {
            "PASS": 0,
            "WARNING": 0,
            "FAIL": 0
        }
        
        failures_log = []
        warnings_log = []
        
        for article in articles:
            report = DataValidator.validate_article(article)
            status = report["status"]
            stats[status] += 1
            
            if status == "FAIL":
                failures_log.append(report)
            elif status == "WARNING":
                warnings_log.append(report)
                
        print("\n" + "=" * 60)
        print("                 VALIDATION RESULTS")
        print("=" * 60)
        print(f"  PASS    : {stats['PASS']} articles")
        print(f"  WARNING : {stats['WARNING']} articles")
        print(f"  FAIL    : {stats['FAIL']} articles")
        print("=" * 60)
        
        if stats["FAIL"] > 0:
            print("\n[!] Top 5 Failure Logs:")
            for item in failures_log[:5]:
                print(f"  - Article ID: {item['article_id']} | Title: '{item['title']}'")
                for issue in item["issues"]:
                    print(f"    * {issue}")
                    
        if stats["WARNING"] > 0:
            print("\n[!] Top 5 Warning Logs:")
            for item in warnings_log[:5]:
                print(f"  - Article ID: {item['article_id']} | Title: '{item['title']}'")
                for issue in item["issues"]:
                    print(f"    * {issue}")
                    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(validate_dataset())
