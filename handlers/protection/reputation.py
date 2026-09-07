from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    count_rep_given_today,
    get_last_rep_given_at,
    get_or_create_chat,
    get_or_create_user,
    get_reputation,
    get_top_reputation,
    give_reputation,
)
from filters.chat_type import IsGroup
from utils.helpers import display_name, escape_html, keep_next
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "reputation"

RATE_COOLDOWN = 30 * 60      # 30 min per giver→target pair per chat
DAILY_REP_LIMIT = 10         # max rep one user can hand out per day


@router.message(Command("rate"), IsGroup())
async def cmd_rate(message: Message) -> None:
    """Give reputation to a user. Usage: /rate <reply>"""
    import datetime

    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Ответь на сообщение пользователя, чтобы поставить репутацию!")
        return

    target = message.reply_to_message.from_user
    giver = message.from_user

    if target.id == giver.id:
        await message.answer("Нельзя ставить оценку самому себе!")
        return
    if target.is_bot:
        await message.answer("Нельзя ставить оценку ботам!")
        return

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        giver_db = await get_or_create_user(session, telegram_id=giver.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)

        # Anti-farm #1: cooldown per (giver → target) pair, persisted in DB.
        last = await get_last_rep_given_at(session, chat.id, user.id, giver_db.id)
        if last is not None:
            elapsed = (datetime.datetime.now() - last).total_seconds()
            if elapsed < RATE_COOLDOWN:
                left = int((RATE_COOLDOWN - elapsed) // 60) + 1
                await message.answer(f"⏳ You already rated this user. Try again in ~{left} min.")
                return

        # Anti-farm #2: daily cap on how many reps a giver may hand out.
        given_today = await count_rep_given_today(session, chat.id, giver_db.id)
        if given_today >= DAILY_REP_LIMIT:
            await message.answer(f"🚫 Daily limit reached ({DAILY_REP_LIMIT} ratings per day).")
            return

        total = await give_reputation(session, chat.id, user.id, giver_db.id)

    name = display_name(target)
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

    name = display_name(target)
    keep_next(message)
    await message.answer(f"⭐ {name} reputation: {rep}")


@router.message(Command("toprep"), IsGroup())
async def cmd_toprep(message: Message) -> None:
    """Show reputation leaderboard."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        top = await get_top_reputation(session, chat.id, limit=10)

    if not top:
        await message.answer("Пока нет оценок!")
        return

    lines = ["🏆 <b>Топ репутации</b>"]
    for i, (user_id, rep) in enumerate(top, 1):
        async with async_session_factory() as session:
            user = await get_or_create_user(session, telegram_id=user_id)
        name = escape_html(user.first_name or f"User {user_id}")
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        lines.append(f"{emoji} {name} — ⭐{rep}")

    keep_next(message)
    await message.answer("\n".join(lines))
