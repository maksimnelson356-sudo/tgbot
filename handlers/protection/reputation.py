from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    get_or_create_chat,
    get_or_create_user,
    get_reputation,
    get_top_reputation,
    give_reputation,
)
from filters.chat_type import IsGroup
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "reputation"

# Cooldown tracking: (chat_id, giver_id) -> timestamp
_cooldowns: dict[tuple[int, int], float] = {}


@router.message(Command("rate"), IsGroup())
async def cmd_rate(message: Message) -> None:
    """Give reputation to a user. Usage: /rate <reply>"""
    import time

    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Reply to a user to give them reputation!")
        return

    target = message.reply_to_message.from_user
    giver = message.from_user

    if target.id == giver.id:
        await message.answer("You can't rate yourself!")
        return
    if target.is_bot:
        await message.answer("You can't rate bots!")
        return

    # Cooldown check (30 min per pair)
    now = time.monotonic()
    key = (message.chat.id, giver.id)
    last = _cooldowns.get(key, 0)
    if now - last < 10:  # 10 seconds to prevent spam
        await message.answer("Wait a bit before rating again!")
        return
    _cooldowns[key] = now

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        total = await give_reputation(session, chat.id, user.id, giver.id)

    name = f"@{target.username}" if target.username else f"<b>{target.first_name}</b>"
    await message.answer(f"⭐ {name} — reputation: {total}")

    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("rep"), IsGroup())
async def cmd_rep(message: Message) -> None:
    """Check reputation. Usage: /rep <reply> or /rep"""
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        rep = await get_reputation(session, chat.id, user.id)

    name = f"@{target.username}" if target.username else f"<b>{target.first_name}</b>"
    await message.answer(f"⭐ {name} reputation: {rep}")


@router.message(Command("toprep"), IsGroup())
async def cmd_toprep(message: Message) -> None:
    """Show reputation leaderboard."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        top = await get_top_reputation(session, chat.id, limit=10)

    if not top:
        await message.answer("No ratings yet!")
        return

    lines = ["🏆 <b>Reputation Top</b>"]
    for i, (user_id, rep) in enumerate(top, 1):
        async with async_session_factory() as session:
            user = await get_or_create_user(session, telegram_id=user_id)
        name = user.first_name or f"User {user_id}"
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        lines.append(f"{emoji} {name} — ⭐{rep}")

    await message.answer("\n".join(lines))
