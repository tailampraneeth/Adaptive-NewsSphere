"""
Seed script for development users (Milestone 4).

Creates:
  - A cold-start user (no interactions, no preference vector)
  - A warm user (interaction_count=10, has UserProfile with muted_categories=['Sports'])
"""

import asyncio
import os
import sys
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.models.user import User
from app.database.models.user_profile import UserProfile


async def seed_users():
    db_url = settings.get_database_url()
    print(f"[*] Connecting to database at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} to seed test users...")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        # Check if cold user already exists
        cold_email = "cold@test.com"
        stmt = select(User).where(User.email == cold_email)
        res = await session.execute(stmt)
        cold_user = res.scalar_one_or_none()

        if not cold_user:
            cold_user = User(
                id=uuid.uuid4(),
                email=cold_email,
                interaction_count=0
            )
            session.add(cold_user)
            print(f"[+] Created cold-start user: {cold_email}")
        else:
            print(f"[*] Cold-start user {cold_email} already exists")

        # Check if warm user already exists
        warm_email = "warm@test.com"
        stmt = select(User).where(User.email == warm_email)
        res = await session.execute(stmt)
        warm_user = res.scalar_one_or_none()

        if not warm_user:
            warm_id = uuid.uuid4()
            warm_user = User(
                id=warm_id,
                email=warm_email,
                interaction_count=10,
                preference_vector_id=str(warm_id)  # mock Qdrant reference
            )
            session.add(warm_user)

            # Create UserProfile for warm user
            profile = UserProfile(
                user_id=warm_id,
                preference_vector_id=str(warm_id),
                interaction_count=10,
                muted_categories=["Sports"],
                muted_publishers=[]
            )
            session.add(profile)
            print(f"[+] Created warm user: {warm_email} with UserProfile muting 'Sports'")
        else:
            # Make sure profile exists
            prof_stmt = select(UserProfile).where(UserProfile.user_id == warm_user.id)
            prof_res = await session.execute(prof_stmt)
            profile = prof_res.scalar_one_or_none()
            if not profile:
                profile = UserProfile(
                    user_id=warm_user.id,
                    preference_vector_id=warm_user.preference_vector_id or str(warm_user.id),
                    interaction_count=warm_user.interaction_count,
                    muted_categories=["Sports"],
                    muted_publishers=[]
                )
                session.add(profile)
                print(f"[+] Restored UserProfile for warm user {warm_email}")
            else:
                print(f"[*] Warm user {warm_email} already exists with profile")

        await session.commit()

        # Refresh to get IDs
        await session.refresh(cold_user)
        await session.refresh(warm_user)

        print("\n--- Seeded User Details ---")
        print(f"Cold User UUID: {cold_user.id} | Email: {cold_user.email}")
        print(f"Warm User UUID: {warm_user.id} | Email: {warm_user.email}")
        print("----------------------------\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_users())
