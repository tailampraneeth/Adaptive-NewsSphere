"""
Seed script for development users (Milestone 4 / Heimdall).

Creates:
  - cold_user: onboarding_complete = False, no profile fields.
  - warm_user: onboarding_complete = True, preferred_categories = ['Technology'], hidden_categories = ['Sports']
"""

import asyncio
import os
import sys
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.models.user import User
from app.utils.auth import hash_password


async def seed_users():
    db_url = settings.get_database_url()
    print(f"[*] Connecting to database to seed test users...")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    default_hash = hash_password("password123")

    async with async_session() as session:
        # Cold user check
        cold_email = "cold@test.com"
        stmt = select(User).where(User.email == cold_email)
        res = await session.execute(stmt)
        cold_user = res.scalar_one_or_none()

        if not cold_user:
            cold_user = User(
                id=uuid.uuid4(),
                email=cold_email,
                hashed_password=default_hash,
                onboarding_complete=False,
                preferred_categories=[],
                preferred_publishers=[],
                hidden_categories=[],
                hidden_publishers=[]
            )
            session.add(cold_user)
            print(f"[+] Created cold-start user: {cold_email}")
        else:
            cold_user.hashed_password = default_hash
            print(f"[*] Cold-start user {cold_email} already exists (password updated)")

        # Warm user check
        warm_email = "warm@test.com"
        stmt = select(User).where(User.email == warm_email)
        res = await session.execute(stmt)
        warm_user = res.scalar_one_or_none()

        if not warm_user:
            warm_user = User(
                id=uuid.uuid4(),
                email=warm_email,
                hashed_password=default_hash,
                name="Warm User",
                country="India",
                state="Telangana",
                city="Hyderabad",
                theme="dark",
                preferred_categories=["Technology", "Business", "Science"],
                preferred_publishers=["reuters", "bbc"],
                hidden_categories=["Sports"],
                hidden_publishers=[],
                onboarding_complete=True,
                brief_time="morning"
            )
            session.add(warm_user)
            print(f"[+] Created warm user: {warm_email}")
        else:
            warm_user.hashed_password = default_hash
            warm_user.name = "Warm User"
            warm_user.country = "India"
            warm_user.preferred_categories = ["Technology", "Business", "Science"]
            warm_user.hidden_categories = ["Sports"]
            warm_user.onboarding_complete = True
            print(f"[*] Warm user {warm_email} already exists (updated)")

        await session.commit()
        await session.refresh(cold_user)
        await session.refresh(warm_user)

        print("\n--- Seeded User Details ---")
        print(f"Cold User UUID: {cold_user.id} | Email: {cold_user.email}")
        print(f"Warm User UUID: {warm_user.id} | Email: {warm_user.email}")
        print("----------------------------\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_users())
