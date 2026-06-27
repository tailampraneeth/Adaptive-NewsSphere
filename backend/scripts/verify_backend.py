import asyncio
import sys
import os
import httpx
from sqlalchemy import text
from redis.asyncio import Redis

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

async def check_postgres() -> bool:
    """Verifies relational database async session connectivity."""
    db_url = settings.get_database_url()
    print(f"[*] Postgres: Connecting to {db_url.split('@')[-1]} ...")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1;"))
            res.scalar()
            print("[PASS] Postgres connection is healthy.")
            return True
    except Exception as e:
        print(f"[FAIL] Postgres connection failed: {e}")
        return False

async def check_redis() -> bool:
    """Verifies Redis Cache connection via ping command."""
    print(f"[*] Redis: Connecting to {settings.REDIS_URL} ...")
    try:
        r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await r.ping()
        if pong:
            print("[PASS] Redis ping responded successfully.")
            return True
        else:
            print("[FAIL] Redis did not respond to ping.")
            return False
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        return False

async def check_qdrant() -> bool:
    """Verifies Qdrant search server HTTP health endpoints."""
    url = f"{settings.QDRANT_URL}/readyz"
    print(f"[*] Qdrant: Connecting to HTTP endpoint {url} ...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                print("[PASS] Qdrant server is running and ready.")
                return True
            else:
                print(f"[FAIL] Qdrant returned status code: {resp.status_code}")
                return False
    except Exception as e:
        print(f"[FAIL] Qdrant connection failed: {e}")
        return False

async def main():
    print("=" * 60)
    print("ADAPTIVE NEWSSPHERE: BACKEND INTEGRATED CONNECTIVITY CHECK")
    print("=" * 60)
    
    pg_ok = await check_postgres()
    print("-" * 60)
    redis_ok = await check_redis()
    print("-" * 60)
    qd_ok = await check_qdrant()
    print("=" * 60)
    
    if pg_ok and redis_ok and qd_ok:
        print("[STATUS: SUCCESS] Backend successfully connected to all three services!")
        sys.exit(0)
    else:
        print("[STATUS: FAILED] Connectivity check failed. Resolve errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
