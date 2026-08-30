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

    # FK cleanup must run on its own connection (outside the DDL transaction):
    # PRAGMA foreign_keys is a no-op inside a transaction.
    if settings.DATABASE_URL.startswith("sqlite"):
        await _drop_stale_fks_sqlite()


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


# Tables whose previous schema declared foreign keys on chat_id / user_id /
# admin_id, but the current models treat those columns as raw Telegram IDs
# (no FK). SQLite cannot DROP a foreign key constraint without rebuilding the
# table, so we detect the stale FK and recreate the table on the fly.
_FK_CLEANUP_TABLES: dict[str, str] = {
    # table_name -> CREATE TABLE statement without the legacy FKs
    "message_log": (
        "CREATE TABLE message_log ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "chat_id INTEGER NOT NULL, "
        "user_id INTEGER NOT NULL, "
        "message_id INTEGER, "
        "text TEXT, "
        "is_deleted BOOLEAN NOT NULL, "
        "created_at DATETIME NOT NULL"
        ")"
    ),
    "action_log": (
        "CREATE TABLE action_log ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "chat_id INTEGER NOT NULL, "
        "user_id INTEGER NOT NULL, "
        "admin_id INTEGER, "
        "action_type VARCHAR(32) NOT NULL, "
        "details TEXT, "
        "created_at DATETIME NOT NULL"
        ")"
    ),
}


async def _drop_stale_fks_sqlite() -> None:
    """Recreate log tables without legacy FKs that no longer match the model.

    The old schema declared FOREIGN KEY(chat_id) REFERENCES chats(id) etc.
    Current models store Telegram IDs in those columns, so the FK is wrong
    and every INSERT fails. Detecting + recreating the table is the only
    way to drop a constraint in SQLite (ALTER TABLE … DROP CONSTRAINT
    is not supported).
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        try:
            for table, create_sql in _FK_CLEANUP_TABLES.items():
                # Does the table exist? If not, nothing to migrate.
                row = await conn.execute(
                    text(
                        "SELECT 1 FROM sqlite_master "
                        "WHERE type='table' AND name=:n"
                    ),
                    {"n": table},
                )
                if row.first() is None:
                    continue

                fk_rows = await conn.execute(
                    text(f"PRAGMA foreign_key_list({table})")
                )
                fks = fk_rows.fetchall()
                if not fks:
                    continue  # already clean

                # Backup rows (preserving column order via SELECT *), drop,
                # recreate, restore. Done in one transaction.
                await conn.execute(text(
                    f"ALTER TABLE {table} RENAME TO _{table}_fk_cleanup"
                ))
                await conn.execute(text(create_sql))
                columns_rows = await conn.execute(
                    text(
                        f"PRAGMA table_info(_{table}_fk_cleanup)"
                    )
                )
                cols = ", ".join(r[1] for r in columns_rows.fetchall())
                await conn.execute(text(
                    f"INSERT INTO {table} ({cols}) "
                    f"SELECT {cols} FROM _{table}_fk_cleanup"
                ))
                await conn.execute(text(f"DROP TABLE _{table}_fk_cleanup"))

                # Reset autoincrement so future inserts start after the
                # restored rows (otherwise INSERTs may collide with old ids).
                await conn.execute(text(
                    f"UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM {table}) WHERE name='{table}'"
                ))
        finally:
            await conn.execute(text("PRAGMA foreign_keys=ON"))


async def get_session() -> AsyncSession:
    """Yield an async session."""
    async with async_session_factory() as session:
        yield session
