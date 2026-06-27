import asyncio
import subprocess
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

async def verify_postgres():
    """Verify async PostgreSQL connection using configured developer credentials."""
    db_url = settings.get_database_url()
    print(f"[Postgres] Attempting connection to: {db_url.split('@')[-1]}")
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            # Run simple query wrapped in text() for SQLAlchemy 2.0 compatibility
            result = await conn.execute(text("SELECT version();"))
            ver = result.scalar()
            print(f"[OK Postgres] Success! Server version: {ver}")
            return True
    except Exception as e:
        print(f"[FAIL Postgres] Connection failed: {e}")
        return False

def verify_docker():
    """Verify that Docker is installed and running in path."""
    print("[Docker] Checking docker command line tools...")
    try:
        # Check docker command exists
        ver = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=True)
        print(f"[OK Docker CLI] Found: {ver.stdout.strip()}")
        
        # Check docker daemon runs
        info = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if info.returncode == 0:
            print("[OK Docker Engine] Daemon is running and healthy.")
            return True
        else:
            print("[FAIL Docker Engine] Daemon is not running. Please start Docker Desktop.")
            return False
    except FileNotFoundError:
        print("[FAIL Docker CLI] Docker command not found. Please install Docker Desktop.")
        return False
    except Exception as e:
        print(f"[FAIL Docker] Verification encountered error: {e}")
        return False

async def main():
    print("=" * 60)
    print("ADAPTIVE NEWSSPHERE: INFRASTRUCTURE VERIFICATION SERVICE")
    print("=" * 60)
    
    docker_ok = verify_docker()
    print("-" * 60)
    postgres_ok = await verify_postgres()
    print("=" * 60)
    
    if docker_ok and postgres_ok:
        print("[SETUP OK] Local infrastructure is fully verified!")
        sys.exit(0)
    else:
        print("[SETUP FAILED] Some dependencies are not configured yet.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
