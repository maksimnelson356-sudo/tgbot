from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.music_service import search_and_download
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "music"


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


@router.message(Command("music"))
async def cmd_music(message: Message) -> None:
    """Search and send music from YouTube. Usage: /music <query>"""
    lang = await get_user_lang(message)
    text = message.text or ""
    query = text.removeprefix("/music").strip()

    if not query:
        await message.answer(t("music_usage", lang))
        return

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
