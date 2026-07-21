from aiogram import BaseMiddleware
from aiogram.types import Message


class AutoDeleteCommandsMiddleware(BaseMiddleware):
    """Automatically delete command messages after processing in groups."""

    async def __call__(self, handler, event: Message, data: dict):
        result = await handler(event, data)

        if event.chat.type in ("group", "supergroup") and event.text:
            if event.text.startswith("/"):
                try:
                    await event.delete()
                except Exception:
                    pass

        return result
