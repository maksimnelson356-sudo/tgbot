import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from services.music_service import search
from utils.i18n import t
from utils.lang_helper import get_user_lang

logger = logging.getLogger(__name__)

router = Router()
router.name = "music"


class MusicState(StatesGroup):
    waiting_query = State()


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


async def _do_search(message: Message, query: str) -> None:
    lang = await get_user_lang(message)
    searching = await message.answer(t("music_searching", lang, query=query))

    result = await search(query)

    if result is None:
        await searching.edit_text(t("music_not_found", lang, query=query))
        return

    duration_str = _format_duration(result.duration) if result.duration else "?"

    try:
        buttons = []
        if result.preview_url:
            buttons.append([InlineKeyboardButton(text="▶️ Превью (30 сек)", url=result.preview_url)])
        if result.url:
            buttons.append([InlineKeyboardButton(text="🔗 Deezer", url=result.url)])
        await message.answer(
            text=t("music_caption", lang, artist=result.artist, title=result.title, duration=duration_str),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None,
        )
        await searching.delete()
    except Exception as e:
        logger.warning("Failed to send music result: %s", e)
        await searching.edit_text(t("music_too_large", lang))


@router.message(Command("music"))
async def cmd_music(message: Message, state: FSMContext) -> None:
    """Search music. /music <query> or /music → ask for query."""
    lang = await get_user_lang(message)
    text = message.text or ""
    bot_info = await message.bot.get_me()
    query = text.removeprefix("/music").removeprefix(f"/music@{bot_info.username}").strip()

    if query:
        await _do_search(message, query)
        return

    await message.answer(t("music_ask_query", lang))
    await state.set_state(MusicState.waiting_query)


@router.message(MusicState.waiting_query)
async def on_music_query(message: Message, state: FSMContext) -> None:
    """Handle the query after user was asked."""
    if message.from_user is None:
        return

    text = message.text or ""
    if text.startswith("/"):
        await state.clear()
        return

    await state.clear()
    await _do_search(message, text)
