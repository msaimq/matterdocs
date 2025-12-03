import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

default_db_path = Path(os.getenv("DATABASE_FILE", "matterdocs.db"))
db_url_env = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = db_url_env or f"sqlite+aiosqlite:///{default_db_path}"

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


async def init_db() -> None:
    """Create all tables defined on the declarative Base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
