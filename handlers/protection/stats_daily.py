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
