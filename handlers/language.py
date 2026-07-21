from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user

router = Router()
router.name = "language"


async def _get_lang(user_id: int) -> str:
    """Get user's language from DB."""
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=user_id)
        return user.language or settings.BOT_LANGUAGE or "ru"


async def _set_lang(user_id: int, lang: str) -> None:
    """Set user's language in DB."""
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=user_id)
        user.language = lang
        await session.commit()


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    text = message.text.removeprefix("/language").strip().lower()

    if text in ("ru", "russian", "русский"):
        await _set_lang(message.from_user.id, "ru")
        await message.answer("✅ Язык установлен: <b>Русский</b>")
        return
    elif text in ("en", "english", "английский"):
        await _set_lang(message.from_user.id, "en")
        await message.answer("✅ Language set: <b>English</b>")
        return

    lang = await _get_lang(message.from_user.id)
    await message.answer(
        "🌐 <b>Выбери язык / Choose language:</b>\n\n"
        "/language ru — 🇷🇺 Русский\n"
        "/language en — 🇬🇧 English"
    )
