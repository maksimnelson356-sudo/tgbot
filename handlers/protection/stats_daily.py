"""Daily message statistics."""
import datetime
from collections import Counter

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.models import MessageLog
from filters.chat_type import IsGroup

router = Router()
router.name = "stats_daily"


@router.message(Command("daystats"), IsGroup())
async def cmd_daystats(message: Message) -> None:
    """Show today's message statistics."""
    today = datetime.datetime.now().date()
    start = datetime.datetime.combine(today, datetime.time.min)

    async with async_session_factory() as session:
        from sqlalchemy import select
        stmt = (
            select(MessageLog.user_id, MessageLog.text)
            .where(
                MessageLog.chat_id == message.chat.id,
                MessageLog.created_at >= start,
                MessageLog.is_deleted == False,
            )
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        await message.answer("📊 No messages today yet.")
        return

    counter = Counter(r[0] for r in rows)
    total = len(rows)

    lines = [f"📊 <b>Today's stats</b> — {total} messages\n"]
    for user_id, count in counter.most_common(10):
        from db.queries import get_or_create_user
        async with async_session_factory() as s:
            user = await get_or_create_user(s, telegram_id=user_id)
        name = user.first_name or f"User {user_id}"
        lines.append(f"  {name}: {count} msgs")

    await message.answer("\n".join(lines))


@router.message(Command("topact"), IsGroup())
async def cmd_topact(message: Message) -> None:
    """Show top active users this week."""
    from sqlalchemy import select, func
    from collections import Counter

    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)

    async with async_session_factory() as session:
        stmt = (
            select(MessageLog.user_id, func.count(MessageLog.id).label("count"))
            .where(
                MessageLog.chat_id == message.chat.id,
                MessageLog.created_at >= week_ago,
                MessageLog.is_deleted == False,
            )
            .group_by(MessageLog.user_id)
            .order_by(func.count(MessageLog.id).desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        await message.answer("📊 No activity this week yet.")
        return

    total = sum(r[1] for r in rows)
    lines = [f"🏆 <b>Top Active (7 days)</b> — {total} messages\n"]
    for i, (user_id, count) in enumerate(rows, 1):
        from db.queries import get_or_create_user
        async with async_session_factory() as s:
            user = await get_or_create_user(s, telegram_id=user_id)
        name = user.first_name or f"User {user_id}"
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        pct = int(count / total * 100) if total else 0
        lines.append(f"{emoji} {name} — {count} ({pct}%)")

    await message.answer("\n".join(lines))
