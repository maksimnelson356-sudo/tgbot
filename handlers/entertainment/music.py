import json
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from services.music_service import search, download_preview, MusicTrack
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


def _build_results_keyboard(tracks: list[MusicTrack], query: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, track in enumerate(tracks):
        label = f"{i+1}. {track.artist} — {track.title} ({_format_duration(track.duration)})"
        payload = json.dumps({"q": query, "i": i})
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"music:{payload}")])
    buttons.append([InlineKeyboardButton(text="🔄 Ещё", callback_data=f"music_more:{query}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("music:"))
async def on_music_pick(callback: CallbackQuery) -> None:
    lang = await get_user_lang(callback)
    data = json.loads(callback.data.removeprefix("music:"))
    query = data["q"]
    idx = data["i"]

    tracks = await search(query, limit=5)
    if idx >= len(tracks):
        await callback.answer("Трек не найден", show_alert=True)
        return

    track = tracks[idx]
    await callback.answer(f"Загружаю {track.artist} — {track.title}...")

    audio = await download_preview(track)
    if audio is None:
        await callback.message.answer("❌ Не удалось загрузить трек")
        return

    duration_str = _format_duration(track.duration)
    await callback.message.answer_audio(
        audio=BufferedInputFile(audio.read(), filename=audio.name),
        title=track.title,
        performer=track.artist,
        duration=track.duration or None,
        caption=f"🎵 {track.artist} — {track.title}\n⏱ {duration_str}",
    )


@router.callback_query(F.data.startswith("music_more:"))
async def on_music_more(callback: CallbackQuery) -> None:
    query = callback.data.removeprefix("music_more:")
    await callback.answer("Ищу ещё...")
    tracks = await search(query, limit=10)
    if not tracks:
        await callback.message.answer(t("music_not_found", "ru", query=query))
        return
    kb = _build_results_keyboard(tracks[:5], query)
    await callback.message.edit_reply_markup(reply_markup=kb)


async def _do_search(message: Message, query: str) -> None:
    lang = await get_user_lang(message)
    searching = await message.answer(t("music_searching", lang, query=query))

    tracks = await search(query, limit=5)

    if not tracks:
        await searching.edit_text(t("music_not_found", lang, query=query))
        return

    kb = _build_results_keyboard(tracks, query)
    await searching.edit_text(
        f"🎶 Найдено по запросу <b>{query}</b>:",
        reply_markup=kb,
    )


@router.message(Command("music"))
async def cmd_music(message: Message, state: FSMContext) -> None:
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
    if message.from_user is None:
        return

    text = message.text or ""
    if text.startswith("/"):
        await state.clear()
        return

    await state.clear()
    await _do_search(message, text)
