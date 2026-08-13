import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


# Ensure the data directory exists (for SQLite)
_db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
_db_dir = os.path.dirname(_db_path)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"timeout": 30},
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables if they don't exist."""
    from db.models import (  # noqa: F401 — import models so they register
        ActionLog,
        BannedSticker,
        Chat,
        ChatAdmin,
        ChatMember,
        GameStats,
        Marriage,
        MessageLog,
        Note,
        Reminder,
        Reputation,
        ScheduledPost,
        User,
        User,
        Warning,
    )

    async with engine.begin() as conn:
        # Enable WAL mode for better concurrent read/write
        if settings.DATABASE_URL.startswith("sqlite"):
            await conn.execute(
                __import__("sqlalchemy").text("PRAGMA journal_mode=WAL")
            )
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Yield an async session."""
    async with async_session_factory() as session:
        yield session
