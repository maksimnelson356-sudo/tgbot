from aiogram import BaseMiddleware
from aiogram.types import Message, ChatMemberUpdated

from db.base import async_session_factory
from db.queries import get_or_create_user, get_or_create_chat, log_message, log_action


class LoggingMiddleware(BaseMiddleware):
    """Logs all messages and chat events to the database."""

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
            await log_message(
                session,
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                message_id=event.message_id,
                text=event.text or event.caption or "",
            )

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
