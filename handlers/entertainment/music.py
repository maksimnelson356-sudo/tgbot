from typing import Optional
import hashlib
import logging
import time

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

from services.music_service import search, download_track
from utils.i18n import t
from utils.lang_helper import get_user_lang

logger = logging.getLogger(__name__)

router = Router()
router.name = "music"

RESULTS_PER_PAGE = 5
CACHE_TTL = 300

# Cache: short_key -> (timestamp, query, tracks)
_cache: dict[str, tuple[float, str, list]] = {}


def _cache_key(query: str) -> str:
    return hashlib.md5(query.encode()).hexdigest()[:8]


def _put_cache(query: str, tracks: list) -> str:
    key = _cache_key(query)
    _cache[key] = (time.time(), query, tracks)
    return key


def _get_cache(key: str) -> Optional[tuple]:
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1], entry[2]
    return None


def _format_duration(duration) -> str:
    if isinstance(duration, str):
        return duration
    if isinstance(duration, (int, float)) and duration > 0:
        m, s = divmod(int(duration), 60)
        return f"{m}:{s:02d}"
    return "?"


def _build_results_keyboard(tracks: list, cache_key: str, page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    start = page * RESULTS_PER_PAGE
    page_tracks = tracks[start:start + RESULTS_PER_PAGE]
    for i, track in enumerate(page_tracks):
        idx = start + i
        dur = f" ({_format_duration(track.duration)})" if track.duration else ""
        label = f"{idx+1}. {track.artist} — {track.title}{dur}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"m:{cache_key}:{idx}")])

    total_pages = (len(tracks) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"mp:{cache_key}:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"mp:{cache_key}:{page+1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _do_search(message: Message, query: str) -> None:
    lang = await get_user_lang(message)
    searching = await message.answer(t("music_searching", lang, query=query))

    tracks = await search(query, limit=20)

    if not tracks:
        await searching.edit_text(t("music_not_found", lang, query=query))
        return

    key = _put_cache(query, tracks)
    kb = _build_results_keyboard(tracks, key, page=0)
    await searching.edit_text(
        f"🎶 <b>{query}</b> — {len(tracks)} треков:",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("mp:"))
async def on_music_page(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    cache_key = parts[1]
    page = int(parts[2])

    entry = _get_cache(cache_key)
    if not entry:
        await callback.answer("Результаты устарели, выполните поиск заново", show_alert=True)
        return

    query, tracks = entry
    kb = _build_results_keyboard(tracks, cache_key, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("m:"))
async def on_music_pick(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    cache_key = parts[1]
    idx = int(parts[2])

    entry = _get_cache(cache_key)
    if not entry:
        await callback.answer("Результаты устарели, выполните поиск заново", show_alert=True)
        return

    query, tracks = entry
    if idx >= len(tracks):
        await callback.answer("Трек не найден", show_alert=True)
        return

    track = tracks[idx]
    await callback.answer(f"📥 {track.artist} — {track.title}")

    audio = await download_track(track)
    if audio is None:
        await callback.message.answer("❌ Не удалось загрузить трек")
        return

    await callback.message.answer_audio(
        audio=BufferedInputFile(audio.read(), filename=audio.name),
        title=track.title,
        performer=track.artist,
        caption=f"🎵 {track.artist} — {track.title}\n⏱ {_format_duration(track.duration)}",
    )


@router.message(Command("music"))
async def cmd_music(message: Message, state: FSMContext) -> None:
    lang = await get_user_lang(message)
    text = message.text or ""
    bot_info = await message.bot.get_me()
    query = text.removeprefix("/music").removeprefix(f"/music@{bot_info.username}").removeprefix(f"@{bot_info.username}").strip()

    if query:
        await _do_search(message, query)
        return

    await message.answer(t("music_ask_query", lang))
    await state.set_state(MusicState.waiting_query)


class MusicState(StatesGroup):
    waiting_query = State()


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
