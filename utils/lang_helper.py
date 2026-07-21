"""Helper to get user's language from database."""

from typing import Union

from aiogram.types import Message, CallbackQuery

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user


async def get_user_lang(event: Union[Message, CallbackQuery]) -> str:
    """Get the user's language setting from DB.

    Falls back to settings.BOT_LANGUAGE or 'ru'.
    """
    user_id = event.from_user.id if event.from_user else None
    if user_id is None:
        return settings.BOT_LANGUAGE or "ru"

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=user_id)
        return user.language or settings.BOT_LANGUAGE or "ru"
