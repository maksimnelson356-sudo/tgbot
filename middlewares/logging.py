import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select

from db.base import async_session_factory
from db.queries import get_or_create_user, get_or_create_chat, log_message, log_action
from utils.helpers import escape_html, spawn

logger = logging.getLogger(__name__)

# XP anti-farm: at most one XP grant per user per cooldown window
_xp_timestamps: dict[int, float] = {}
_XP_COOLDOWN = 30.0
_XP_PER_MESSAGE = 1


def _member_xp(session, chat_pk: int, user_pk: int):
    from db.models import ChatMember
    stmt = select(ChatMember.xp).where(
        ChatMember.chat_id == chat_pk, ChatMember.user_id == user_pk
    )
    return session.execute(stmt).scalar_one_or_none()


class LoggingMiddleware(BaseMiddleware):
    """Logs all messages and chat events to the database + awards XP."""

    async def __call__(self, handler, event, data: dict):
        if isinstance(event, Message):
            await self._log_message(event)
        elif isinstance(event, ChatMemberUpdated):
            await self._log_chat_member(event)

        return await handler(event, data)

    async def _log_message(self, event: Message) -> None:
        if event.from_user is None or event.chat is None:
            return
        if event.from_user.is_bot:
            return

        async with async_session_factory() as session:
            user = await get_or_create_user(
                session,
                telegram_id=event.from_user.id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
            )
            chat = await get_or_create_chat(
                session,
                telegram_id=event.chat.id,
                title=getattr(event.chat, "title", None),
                chat_type=event.chat.type,
            )
            await log_message(
                session,
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                message_id=event.message_id,
                text=event.text or event.caption or "",
            )

            # XP for activity (group chats only, rate-limited)
            if event.chat.type in ("group", "supergroup"):
                self._maybe_award_xp(event, chat.id, user.id)

    def _maybe_award_xp(self, event: Message, chat_pk: int, user_pk: int) -> None:
        from db.queries import add_xp, level_for_xp

        now = time.monotonic()
        last = _xp_timestamps.get(user_pk, 0)
        if now - last < _XP_COOLDOWN:
            return
        _xp_timestamps[user_pk] = now

        async def _award() -> None:
            try:
                async with async_session_factory() as s:
                    old_level = level_for_xp(_member_xp(s, chat_pk, user_pk) or 0)
                    _, new_level = await add_xp(s, chat_pk, user_pk, _XP_PER_MESSAGE)
                if new_level > old_level:
                    u = event.from_user
                    name = (
                        f"@{u.username}" if u.username
                        else f'<a href="tg://user?id={u.id}">'
                        f'{escape_html(u.first_name or "User")}</a>'
                    )
                    await event.bot.send_message(
                        event.chat.id,
                        f"🎉 <b>Level up!</b> {name} — уровень <b>{new_level}</b>! "
                        f"Текущий ранг: /rank",
                    )
            except Exception as e:
                logger.warning("XP award failed: %s", e)

        spawn(_award(), name=f"xp_{user_pk}")

    async def _log_chat_member(self, event: ChatMemberUpdated) -> None:
        if event.from_user is None or event.chat is None:
            return

        new_status = event.new_chat_member.status
        old_status = event.old_chat_member.status

        action_type = None
        if new_status == "member" and old_status in ("left", "kicked"):
            action_type = "joined"
        elif new_status in ("left", "kicked") and old_status == "member":
            action_type = "left"
        elif new_status == "kicked":
            action_type = "banned"
        elif old_status == "kicked" and new_status == "member":
            action_type = "unbanned"

        if action_type is None:
            return

        async with async_session_factory() as session:
            await get_or_create_user(
                session,
                telegram_id=event.from_user.id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
            )
            await get_or_create_chat(
                session,
                telegram_id=event.chat.id,
                title=getattr(event.chat, "title", None),
                chat_type=event.chat.type,
            )
            await log_action(
                session,
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                action_type=action_type,
                details=f"From: {old_status} → To: {new_status}",
            )
