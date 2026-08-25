"""Engagement hooks driven by the background scheduler:
- birthday auto-congratulations (daily)
- weekly digest with tops (Mondays)
"""
import datetime
import logging

from db.base import async_session_factory
from db.models import Chat, User
from sqlalchemy import select

logger = logging.getLogger(__name__)

_last_birthday_date: datetime.date | None = None
_last_digest_date: datetime.date | None = None


async def _group_chats(session):
    stmt = select(Chat).where(Chat.type.in_(("group", "supergroup")))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _name_for(session, telegram_id: int) -> tuple[str, str]:
    """Returns (html_name, username_or_empty)."""
    from db.queries import get_or_create_user
    user = await get_or_create_user(session, telegram_id=telegram_id)
    if user.username:
        return f"@{user.username}", user.username
    name = (user.first_name or f"User {telegram_id}").strip()
    import html as _html
    return _html.escape(name), ""


def _mention(name_html: str, username: str, telegram_id: int) -> str:
    if username:
        return f"@{username}"
    return f'<a href="tg://user?id={telegram_id}">{name_html}</a>'


async def check_birthdays(bot) -> None:
    """Once a day: congratulate members whose birthday is today."""
    global _last_birthday_date
    today = datetime.date.today()
    if _last_birthday_date == today:
        return
    _last_birthday_date = today

    today_str = f"{today.day:02d}.{today.month:02d}"
    try:
        async with async_session_factory() as session:
            chats = await _group_chats(session)
            for chat in chats:
                settings = chat.settings or {}
                if not settings.get("birthday_greetings_enabled", True):
                    continue
                bdays = settings.get("birthdays") or {}
                targets = [uid for uid, date in bdays.items() if date == today_str]
                if not targets:
                    continue
                names = []
                for uid in targets[:5]:
                    name_html, username = await _name_for(session, int(uid))
                    names.append(_mention(name_html, username, int(uid)))
                try:
                    await bot.send_message(
                        chat.telegram_id,
                        f"🎂🎉 Сегодня день рождения у {' и '.join(names)}!\n"
                        f"Поздравляем! Желаешь отличного года! 🥳",
                    )
                    logger.info("Birthday greeting sent in chat %s for %s", chat.telegram_id, targets)
                except Exception as e:
                    logger.warning("Birthday send failed in %s: %s", chat.telegram_id, e)
    except Exception as e:
        logger.warning("check_birthdays failed: %s", e)


async def weekly_digest(bot) -> None:
    """Mondays: post a digest with activity/reputation/xp tops."""
    global _last_digest_date
    today = datetime.date.today()
    if today.weekday() != 0 or _last_digest_date == today:
        return
    _last_digest_date = today

    medals = ["🥇", "🥈", "🥉"]
    try:
        async with async_session_factory() as session:
            chats = await _group_chats(session)
            for chat in chats:
                settings = chat.settings or {}
                if not settings.get("weekly_digest_enabled", True):
                    continue

                from db.queries import top_xp, get_top_reputation
                xp_list = await top_xp(session, chat.id, limit=3)
                rep_list = await get_top_reputation(session, chat.id, limit=3)

                lines = ["📊 <b>Итоги недели</b>", ""]

                if xp_list:
                    lines.append("🔥 <b>Самые активные:</b>")
                    for i, (tg_id, xp, level) in enumerate(xp_list):
                        name_html, username = await _name_for(session, tg_id)
                        medal = medals[i] if i < 3 else "▫️"
                        lines.append(f"  {medal} {_mention(name_html, username, tg_id)} — LVL {level}")
                    lines.append("")

                if rep_list:
                    lines.append("⭐ <b>Топ по репутации:</b>")
                    for i, (tg_id, rep) in enumerate(rep_list):
                        name_html, username = await _name_for(session, tg_id)
                        medal = medals[i] if i < 3 else "▫️"
                        lines.append(f"  {medal} {_mention(name_html, username, tg_id)} — {rep}")
                    lines.append("")

                if len(lines) <= 2:
                    continue  # nothing to show yet

                lines.append("🎁 Не забудь /daily и проверь свой /rank!")

                try:
                    await bot.send_message(chat.telegram_id, "\n".join(lines))
                    logger.info("Weekly digest sent to chat %s", chat.telegram_id)
                except Exception as e:
                    logger.warning("Digest send failed in %s: %s", chat.telegram_id, e)
    except Exception as e:
        logger.warning("weekly_digest failed: %s", e)
