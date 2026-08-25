import os

from sqlalchemy import event
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


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
    """SQLite pragmas on every new connection."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
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
        Warning,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.DATABASE_URL.startswith("sqlite"):
            await _migrate_sqlite(conn)


_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    # table -> [(column, DDL fragment)]
    "chat_members": [
        ("xp", "INTEGER NOT NULL DEFAULT 0"),
        ("daily_streak", "INTEGER NOT NULL DEFAULT 0"),
        ("last_daily_at", "DATETIME NULL"),
        ("invited_by", "INTEGER NULL"),
    ],
    "users": [
        ("referred_by", "INTEGER NULL"),
    ],
}


async def _migrate_sqlite(conn) -> None:
    """Add columns that create_all can't add to existing tables."""
    from sqlalchemy import text

    for table, columns in _MIGRATIONS.items():
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result.fetchall()}
        for col_name, col_ddl in columns:
            if col_name not in existing:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_ddl}")
                )


async def get_session() -> AsyncSession:
    """Yield an async session."""
    async with async_session_factory() as session:
        yield session
