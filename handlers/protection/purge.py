from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "purge"


@router.message(Command("purge"), IsGroup(), HasRank(2))
async def cmd_purge(message: Message) -> None:
    """Delete multiple messages at once. Usage: /purge [N] (reply to a message)"""
    if message.reply_to_message is None:
        await message.answer("Reply to the first message to delete from.")
        return

    # Parse number of messages to delete (default 10)
    args = message.text.removeprefix("/purge").strip()
    try:
        count = int(args) if args else 10
        count = max(1, min(count, 100))  # Limit to 1-100
    except ValueError:
        count = 10

    reply_msg_id = message.reply_to_message.message_id
    current_msg_id = message.message_id

    deleted = 0
    for msg_id in range(reply_msg_id, current_msg_id + 1):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            deleted += 1
        except Exception:
            pass

    # Send confirmation and auto-delete it
    confirm = await message.answer(f"✅ Purged {deleted} messages.")
    try:
        import asyncio
        await asyncio.sleep(3)
        await confirm.delete()
    except Exception:
        pass
