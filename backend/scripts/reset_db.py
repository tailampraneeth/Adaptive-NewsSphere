import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

url = settings.get_database_url()
engine = create_async_engine(url)

async def reset():
    print("=" * 60)
    print("      RESETTING POSTGRESQL DATABASE SCHEMA")
    print("=" * 60)
    async with engine.begin() as conn:
        print("[*] Dropping schema public...")
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        print("[*] Creating schema public...")
        await conn.execute(text("CREATE SCHEMA public;"))
        print("[*] Restoring public schema default privileges...")
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        print("[OK] Database schema reset successfully!")

if __name__ == "__main__":
    asyncio.run(reset())
