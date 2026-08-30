"""Slow mode middleware — limit messages per user per interval."""
import time

from aiogram import BaseMiddleware
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat


class SlowModeMiddleware(BaseMiddleware):
    """Allows max N messages per M seconds per user (configurable per chat)."""

    def __init__(self) -> None:
        self.history: dict[tuple[int, int], float] = {}
        super().__init__()

    def _prune_history(self, now: float) -> None:
        """Drop entries idle longer than 10 minutes, keeping the dict bounded."""
        if len(self.history) < 1000:
            return
        cutoff = now - 600
        stale = [k for k, ts in self.history.items() if ts < cutoff]
        for k in stale:
            self.history.pop(k, None)

    async def __call__(self, handler, event: Message, data: dict):
        if event.from_user is None or event.chat is None:
            return await handler(event, data)

        # Check if slow mode is enabled for this chat
        async with async_session_factory() as session:
            chat = await get_or_create_chat(session, telegram_id=event.chat.id)
            delay = (chat.settings or {}).get("slowmode_delay", 0)

        if delay <= 0:
            return await handler(event, data)

        # Skip admins
        try:
            member = await event.chat.get_member(event.from_user.id)
            if member.status in ("creator", "administrator"):
                return await handler(event, data)
        except Exception:
            pass

        now = time.monotonic()
        key = (event.chat.id, event.from_user.id)
        last = self.history.get(key, 0)

        if now - last < delay:
            try:
                await event.delete()
            except Exception:
                pass
            return  # Drop message

        self._prune_history(now)
        self.history[key] = now
        return await handler(event, data)
