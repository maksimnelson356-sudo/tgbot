"""Set log channel for chat events."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, update_chat_settings
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "setlog"


@router.message(Command("setlog"), IsGroup(), HasRank(2))
async def cmd_setlog(message: Message) -> None:
    """Set log channel. Forward a message from the target channel with /setlog"""
    if message.forward_from_chat:
        log_id = message.forward_from_chat.id
    elif message.reply_to_message and message.reply_to_message.sender_chat:
        log_id = message.reply_to_message.sender_chat.id
    else:
        await message.answer("Forward a message from the channel you want as log, or reply to a channel message.")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await update_chat_settings(session, chat.id, {"log_chat_id": log_id})

    await message.answer(f"✅ Log channel set! Events will be forwarded there.")


@router.message(Command("remlog"), IsGroup(), HasRank(2))
async def cmd_remlog(message: Message) -> None:
    """Remove log channel."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await update_chat_settings(session, chat.id, {"log_chat_id": None})

    await message.answer("✅ Log channel removed.")
