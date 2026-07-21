from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user

router = Router()
router.name = "feedback"


@router.message(Command("feedback"))
async def cmd_feedback(message: Message) -> None:
    """Send feedback to the bot owner. Usage: /feedback <text>"""
    text = message.text.removeprefix("/feedback").strip()
    if not text:
        await message.answer("Usage: /feedback <your message>")
        return

    owner_id = settings.OWNER_ID
    if not owner_id:
        await message.answer("Bot owner not configured.")
        return

    try:
        await message.bot.send_message(
            owner_id,
            f"💬 <b>Feedback</b>\n\n"
            f"From: {message.from_user.first_name} (ID: {message.from_user.id})\n"
            f"Chat: {message.chat.title or 'PM'}\n"
            f"Message: {text}",
        )
        await message.answer("✅ Feedback sent to owner!")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
