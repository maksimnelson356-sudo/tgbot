from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    ban_sticker, get_or_create_chat, get_or_create_user, is_sticker_banned,
    list_banned_stickers, unban_sticker,
)
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "bansticker"


@router.message(Command("bansticker"), IsGroup(), HasRank(2), F.reply_to_message)
async def cmd_bansticker(message: Message) -> None:
    """Ban a sticker. Usage: reply to sticker with /bansticker"""
    sticker = message.reply_to_message.sticker
    if sticker is None:
        await message.answer("Reply to a sticker to ban it!")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        await ban_sticker(
            session, chat.id, sticker.file_unique_id,
            sticker.emoji, user.id,
        )

    await message.answer(f"🚫 Sticker banned! Emoji: {sticker.emoji}")
    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("unbansticker"), IsGroup(), HasRank(2))
async def cmd_unbansticker(message: Message) -> None:
    """Unban a sticker. Usage: reply to sticker with /unbansticker"""
    if not message.reply_to_message or not message.reply_to_message.sticker:
        await message.answer("Reply to a sticker to unban it!")
        return

    sticker = message.reply_to_message.sticker
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        ok = await unban_sticker(session, chat.id, sticker.file_unique_id)

    await message.answer("✅ Sticker unbanned!" if ok else "❌ Sticker not found in ban list.")


@router.message(Command("listbanned"), IsGroup(), HasRank(2))
async def cmd_listbanned(message: Message) -> None:
    """List all banned stickers in this chat."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        banned = await list_banned_stickers(session, chat.id)

    if not banned:
        await message.answer("No banned stickers.")
        return

    lines = ["🚫 <b>Banned stickers:</b>"]
    for i, bs in enumerate(banned, 1):
        lines.append(f"{i}. {bs.emoji or '❓'} (ID: {bs.file_unique_id[:12]}...)")

    await message.answer("\n".join(lines))
