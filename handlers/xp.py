"""XP/levels: /rank shows level progress, /daily claims the streak bonus."""
import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    claim_daily,
    get_chat_member,
    get_or_create_chat,
    get_or_create_user,
    get_top_inviters,
    top_xp,
    xp_for_level,
)
from filters.chat_type import IsGroup
from utils.helpers import escape_html, keep_next

router = Router()
router.name = "xp"

_TITLES = [
    (0, "🥱 Новичок"),
    (1, "🌱 Активист"),
    (3, "💬 Знаток чата"),
    (6, "🔥 Легенда"),
    (10, "👑 Мифический"),
]


def _title(level: int) -> str:
    current = _TITLES[0][1]
    for min_level, title in _TITLES:
        if level >= min_level:
            current = title
    return current


@router.message(Command("rank"), IsGroup())
async def cmd_rank(message: Message) -> None:
    """Show your (or replied user's) XP level and progress."""
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        member = await get_chat_member(session, chat.id, user.id)

    if member is None:
        await message.answer("Профиль не найден — напиши что-нибудь в чат!")
        return

    xp = member.xp or 0
    streak = member.daily_streak or 0
    level = int((xp // 100) ** 0.5) if xp > 0 else 0
    cur_floor = xp_for_level(level)
    next_floor = xp_for_level(level + 1)
    need = next_floor - xp
    done = xp - cur_floor
    span = max(next_floor - cur_floor, 1)
    filled = min(int(done * 10 / span), 10)
    bar = "█" * filled + "░" * (10 - filled)

    name = f"@{target.username}" if target.username else escape_html(target.first_name or "User")

    lines = [
        f"🏅 <b>{name}</b> — {_title(level)}",
        f"⭐ Уровень <b>{level}</b> • {xp} XP",
        f"[{bar}] {done}/{span} до уровня {level + 1}",
        f"🔥 Стрик /daily: <b>{streak}</b> дн.",
    ]
    keep_next(message)
    await message.answer("\n".join(lines))


@router.message(Command("daily"), IsGroup())
async def cmd_daily(message: Message) -> None:
    """Claim the daily streak bonus (XP reward grows with the streak)."""
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        claimed, streak, reward = await claim_daily(session, chat.id, user.id)

    if claimed:
        await message.answer(
            f"🎁 Дневной бонус получен: <b>+{reward} XP</b>\n"
            f"🔥 Стрик: <b>{streak}</b> дн. подряд — не пропускай!"
        )
    else:
        now = datetime.datetime.now()
        tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        left_h = max(int((tomorrow - now).total_seconds() // 3600), 0)
        left_m = max(int(((tomorrow - now).total_seconds() % 3600) // 60), 1)
        await message.answer(
            f"⏳ Бонус уже получен сегодня. Возвращайся через ~{left_h}ч {left_m}мин.\n"
            f"(текущий стрик: {streak})"
        )


@router.message(Command("topxp"), IsGroup())
async def cmd_topxp(message: Message) -> None:
    """XP leaderboard."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        rows = await top_xp(session, chat.id, limit=10)

    if not rows:
        await message.answer("Пока никто не набрал XP — начни общаться!")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ по опыту</b>"]
    for i, (tg_id, xp, level) in enumerate(rows):
        medal = medals[i] if i < 3 else "▫️"
        lines.append(f"{medal} {_name_by_tg(tg_id)} — LVL {level} • {xp} XP")
    keep_next(message)
    await message.answer("\n".join(lines))


async def _name_by_tg(telegram_id: int) -> str:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=telegram_id)
    return f"@{user.username}" if user.username else escape_html(user.first_name or f"User {telegram_id}")


@router.message(Command("inviters"), IsGroup())
async def cmd_inviters(message: Message) -> None:
    """Top members by number of people they invited."""
    from db.queries import count_invites

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        top = await get_top_inviters(session, chat.id, limit=10)

    if not top:
        await message.answer(
            "Пока нет данных о приглашениях.\n"
            "Приглашай друзей по своей ссылке: t.me/"
            f"{(await message.bot.get_me()).username}?start=ref_{message.from_user.id}"
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🫂 <b>Топ приглашателей</b>"]
    for i, (inviter_pk, cnt) in enumerate(top):
        medal = medals[i] if i < 3 else "▫️"
        tg_id = await _tg_of_pk(inviter_pk)
        name = await _name_by_tg(tg_id) if tg_id else f"User#{inviter_pk}"
        lines.append(f"{medal} {name} — {cnt} 🎯")

    lines.append("")
    ref_link = f"t.me/{(await message.bot.get_me()).username}?start=ref_{message.from_user.id}"
    lines.append(f"🔗 Твоя ссылка: {ref_link}")
    keep_next(message)
    await message.answer("\n".join(lines))


async def _tg_of_pk(user_pk: int) -> int | None:
    from sqlalchemy import select
    from db.models import User
    async with async_session_factory() as session:
        row = (await session.execute(select(User.telegram_id).where(User.id == user_pk))).first()
    return row[0] if row else None
