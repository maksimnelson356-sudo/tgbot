from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from services.music_service import search_and_download
from utils.i18n import t
from utils.lang_helper import get_user_lang

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

    result = await search_and_download(query)

    if result is None:
        await searching.edit_text(t("music_not_found", lang, query=query))
        return

    duration_str = _format_duration(result.duration) if result.duration else "?"

    try:
        result.audio.seek(0)
        await message.answer_audio(
            audio=result.audio,
            title=result.title,
            duration=result.duration or None,
            caption=t("music_caption", lang, duration=duration_str),
        )
        await searching.delete()
    except Exception:
        await searching.edit_text(t("music_too_large", lang))


@router.message(Command("music"))
async def cmd_music(message: Message, state: FSMContext) -> None:
    """Search music. /music <query> or /music → ask for query."""
    lang = await get_user_lang(message)
    text = message.text or ""
    query = text.removeprefix("/music").strip()

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
