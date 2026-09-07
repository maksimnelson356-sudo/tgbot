"""Slow mode commands for admins."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, set_chat_setting
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "slowmode_cmd"


@router.message(Command("slowmode"), IsGroup(), HasRank(2))
async def cmd_slowmode(message: Message) -> None:
    """Set slow mode delay. Usage: /slowmode <seconds>"""
    args = message.text.removeprefix("/slowmode").strip()
    if not args:
        # Show current setting
        async with async_session_factory() as session:
            chat = await get_or_create_chat(session, telegram_id=message.chat.id)
            delay = (chat.settings or {}).get("slowmode_delay", 0)
        status = f"🐌 Медленный режим: {delay}с" if delay > 0 else "🐌 Медленный режим: ВЫКЛ"
        await message.answer(f"{status}\nИспользование: /slowmode <секунды> (0 = выключить)")
        return

    try:
        delay = max(0, min(int(args), 3600))
    except ValueError:
        await message.answer("Неверное число.")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await set_chat_setting(session, chat.id, "slowmode_delay", delay)

    if delay > 0:
        await message.answer(f"🐌 Медленный режим: <b>{delay}с</b> между сообщениями.")
    else:
        await message.answer("🐌 Медленный режим выключен.")
