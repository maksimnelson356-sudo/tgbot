"""Slow mode commands for admins."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, update_chat_settings
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
        status = f"🐌 Slow mode: {delay}s" if delay > 0 else "🐌 Slow mode: OFF"
        await message.answer(f"{status}\nUsage: /slowmode <seconds> (0 to disable)")
        return

    try:
        delay = max(0, min(int(args), 3600))
    except ValueError:
        await message.answer("Invalid number.")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await update_chat_settings(session, chat.id, {"slowmode_delay": delay})

    if delay > 0:
        await message.answer(f"🐌 Slow mode set to {delay}s between messages.")
    else:
        await message.answer("🐌 Slow mode disabled.")
