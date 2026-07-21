"""Forward events to a configured log channel."""
from aiogram import Bot

from db.base import async_session_factory
from db.queries import get_or_create_chat


async def send_log(bot: Bot, chat_id: int, text: str) -> None:
    """Send a log message to the configured log channel for this chat."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=chat_id)
        log_channel = (chat.settings or {}).get("log_chat_id")
        if not log_channel:
            return
    try:
        await bot.send_message(chat_id=log_channel, text=text)
    except Exception:
        pass
