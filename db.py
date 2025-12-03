import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

# Railway provides DATABASE_URL for PostgreSQL
db_url_env = os.getenv("DATABASE_URL", "").strip()

if db_url_env:
    # Production: Use Railway's PostgreSQL
    if db_url_env.startswith("postgres://"):
        # Fix for SQLAlchemy 2.0 compatibility
        DATABASE_URL = db_url_env.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url_env.startswith("postgresql://"):
        # Also fix postgresql:// to use asyncpg
        DATABASE_URL = db_url_env.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        DATABASE_URL = db_url_env
    print(f"🔗 Using PostgreSQL (async): {DATABASE_URL[:50]}...")
else:
    # Local development: Use SQLite with async driver
    default_db_path = Path(os.getenv("DATABASE_FILE", "matterdocs.db"))
    DATABASE_URL = f"sqlite+aiosqlite:///{default_db_path}"
    print(f"🔗 Using SQLite: {DATABASE_URL}")

try:
    print(f"🔧 Final DATABASE_URL: {DATABASE_URL[:60]}...")
    engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
    print("✅ Database engine created successfully")
except Exception as e:
    print(f"❌ Database engine creation failed: {e}")
    print(f"❌ Failed URL was: {DATABASE_URL[:60]}...")
    # Fallback to a minimal in-memory SQLite for health checks
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
    print("⚠️ Using fallback in-memory database")
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


async def init_db() -> None:
    """Create all tables defined on the declarative Base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
