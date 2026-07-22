from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from db.base import async_session_factory
from db.queries import (
    add_scheduled_post,
    delete_scheduled_post,
    get_scheduled_posts,
    get_or_create_chat,
)
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "scheduler"


class ScheduleState(StatesGroup):
    waiting_text = State()
    waiting_photo = State()
    waiting_interval = State()


def _skip_kb(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=t("skip", lang))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def _interval_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for h in [1, 2, 3, 4, 6, 8, 12, 24]:
        builder.button(text=f"{h}ч")
    builder.adjust(4)
    return builder.as_markup(resize_keyboard=True)


@router.message(Command("schedule"), IsGroup(), HasRank(2))
async def cmd_schedule(message: Message, state: FSMContext) -> None:
    """Create a scheduled post. FSM flow."""
    lang = await get_user_lang(message)
    await message.answer(t("schedule_ask_text", lang), reply_markup=_skip_kb(lang))
    await state.set_state(ScheduleState.waiting_text)


@router.message(ScheduleState.waiting_text)
async def on_schedule_text(message: Message, state: FSMContext) -> None:
    lang = await get_user_lang(message)
    if message.text and message.text == t("skip", lang):
        await state.update_data(text="")
    else:
        await state.update_data(text=message.text or "")

    await message.answer(t("schedule_ask_photo", lang), reply_markup=_skip_kb(lang))
    await state.set_state(ScheduleState.waiting_photo)


@router.message(ScheduleState.waiting_photo)
async def on_schedule_photo(message: Message, state: FSMContext) -> None:
    lang = await get_user_lang(message)

    if message.photo:
        await state.update_data(media_file_id=message.photo[-1].file_id, media_type="photo")
    elif message.video:
        await state.update_data(media_file_id=message.video.file_id, media_type="video")
    elif message.animation:
        await state.update_data(media_file_id=message.animation.file_id, media_type="animation")
    elif message.document:
        await state.update_data(media_file_id=message.document.file_id, media_type="document")
    elif message.voice:
        await state.update_data(media_file_id=message.voice.file_id, media_type="voice")
    elif message.audio:
        await state.update_data(media_file_id=message.audio.file_id, media_type="audio")
    elif message.video_note:
        await state.update_data(media_file_id=message.video_note.file_id, media_type="video_note")
    elif message.text and message.text == t("skip", lang):
        await state.update_data(media_file_id=None, media_type=None)
    else:
        await message.answer(t("schedule_ask_media_again", lang))
        return

    await message.answer(t("schedule_ask_interval", lang), reply_markup=_interval_kb())
    await state.set_state(ScheduleState.waiting_interval)


@router.message(ScheduleState.waiting_interval)
async def on_schedule_interval(message: Message, state: FSMContext) -> None:
    lang = await get_user_lang(message)

    text = (message.text or "").strip().lower().replace("ч", "").replace("h", "")
    if not text.isdigit() or int(text) < 1 or int(text) > 24:
        await message.answer(t("schedule_invalid_interval", lang))
        return

    interval = int(text)
    data = await state.get_data()
    await state.clear()

    post_text = data.get("text", "")
    media_file_id = data.get("media_file_id")
    media_type = data.get("media_type")

    if not post_text and not media_file_id:
        await message.answer(t("schedule_empty", lang))
        return

    async with async_session_factory() as session:
        post = await add_scheduled_post(
            session,
            chat_telegram_id=message.chat.id,
            text=post_text,
            interval_hours=interval,
            created_by=message.from_user.id,
            photo_file_id=media_file_id,
            media_type=media_type,
        )

    await message.answer(
        t("schedule_created", lang, id=post.id, interval=interval),
        reply_markup=None,
    )


@router.message(Command("schedule_list"), IsGroup(), HasRank(2))
async def cmd_schedule_list(message: Message) -> None:
    """List active scheduled posts."""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        posts = await get_scheduled_posts(session, message.chat.id)

    if not posts:
        await message.answer(t("schedule_none", lang))
        return

    lines = [t("schedule_list_title", lang)]
    for p in posts:
        _media_emoji = {"photo": "📷", "video": "🎬", "animation": "🎞", "document": "📄", "voice": "🎤", "audio": "🎵", "video_note": " circle "}
        media = _media_emoji.get(p.media_type or "", "📎" if p.photo_file_id else "📝")
        lines.append(f"• #{p.id} {media} {(p.text or '—')[:50]} (каждые {p.interval_hours}ч)")
    await message.answer("\n".join(lines))


@router.message(Command("schedule_del"), IsGroup(), HasRank(2))
async def cmd_schedule_del(message: Message) -> None:
    """Delete a scheduled post. /schedule_del <id>"""
    lang = await get_user_lang(message)
    args = message.text.removeprefix("/schedule_del").strip()

    if not args.isdigit():
        await message.answer(t("schedule_del_usage", lang))
        return

    post_id = int(args)
    async with async_session_factory() as session:
        deleted = await delete_scheduled_post(session, post_id)

    if deleted:
        await message.answer(t("schedule_deleted", lang, id=post_id))
    else:
        await message.answer(t("schedule_not_found", lang, id=post_id))
