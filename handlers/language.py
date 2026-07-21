from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user
from utils.i18n import t as _t

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
    """Show language selection."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.adjust(2)

    # Determine current language for the prompt
    lang = await _get_lang(message.from_user.id)

    # Show in both languages
    await message.answer(
        "🌐 <b>Выбери язык / Choose language:</b>",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def lang_callback(callback: CallbackQuery) -> None:
    """Handle language selection."""
    lang = callback.data.split(":")[1]
    if lang not in ("ru", "en"):
        await callback.answer("Invalid language")
        return

    await _set_lang(callback.from_user.id, lang)

    response_text = (
        "✅ Язык установлен: <b>Русский</b>"
        if lang == "ru"
        else "✅ Language set: <b>English</b>"
    )

    await callback.message.edit_text(response_text)
    await callback.answer()
