from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "zombies"


@router.message(Command("zombies"), IsGroup(), HasRank(2))
async def cmd_zombies(message: Message) -> None:
    """Remove deleted accounts from the chat."""
    status_msg = await message.answer("🔍 Scanning for deleted accounts...")

    try:
        count = 0
        kicked = 0
        async for member in message.chat.get_members():
            count += 1
            # Deleted Telegram accounts have id = 777000 or user.is_bot = False but no name
            user = member.user
            if user.is_bot:
                continue
            # "Deleted Account" users have no first_name or have specific pattern
            if not user.first_name or user.first_name == "":
                try:
                    await message.chat.ban(user_id=user.id)
                    kicked += 1
                except Exception:
                    pass

        await status_msg.edit_text(
            f"✅ <b>Zombie cleanup complete!</b>\n"
            f"👥 Total members checked: {count}\n"
            f"🧟 Deleted accounts removed: {kicked}"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}. Make sure bot is admin!")
