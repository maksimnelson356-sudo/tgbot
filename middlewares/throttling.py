import time

from aiogram import BaseMiddleware
from aiogram.types import Message

from typing import Optional

from config import settings


class ThrottlingMiddleware(BaseMiddleware):
    """Token-bucket rate limiter per (chat_id, user_id).

    Если пользователь превышает лимит, его сообщение удаляется (в группах)
    и он получает предупреждение.
    """

    def __init__(
        self,
        rate_limit: Optional[int] = None,
        burst_limit: Optional[int] = None,
    ) -> None:
        self.rate_limit = rate_limit or settings.THROTTLE_MESSAGES
        self.window = settings.THROTTLE_WINDOW
        self.burst_limit = burst_limit or settings.THROTTLE_BURST
        self.burst_window = settings.THROTTLE_BURST_WINDOW
        # Key: (chat_id, user_id) -> list of timestamps
        self.history: dict[tuple[int, int], list[float]] = {}
        super().__init__()

    async def __call__(self, handler, event: Message, data: dict):
        if event.from_user is None or event.chat is None:
            return await handler(event, data)

        chat_id = event.chat.id
        user_id = event.from_user.id
        now = time.monotonic()
        key = (chat_id, user_id)

        # Clean old entries
        if key in self.history:
            self.history[key] = [
                t for t in self.history[key]
                if now - t < self.burst_window
            ]
        else:
            self.history[key] = []

        # Check burst limit
        if len(self.history[key]) >= self.burst_limit:
            # Too many messages in window
            try:
                await event.delete()
            except Exception:
                pass
            return  # Drop the update — don't call handler

        # Check short-window limit
        recent = [t for t in self.history[key] if now - t < self.window]
        if len(recent) >= self.rate_limit:
            try:
                await event.delete()
            except Exception:
                pass
            # Don't even store this attempt
            return

        # Record this message
        self.history[key].append(now)
        return await handler(event, data)
