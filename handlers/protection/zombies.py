from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "zombies"


@router.message(Command("zombies"), IsGroup(), HasRank(2))
async def cmd_zombies(message: Message) -> None:
    """Remove deleted/deactivated accounts from the chat.

    Telegram Bot API doesn't support listing all members, so we iterate
    DB-tracked members and check each one via get_chat_member.
    """
    status_msg = await message.answer("🔍 Scanning for deleted accounts...")

    try:
        async with async_session_factory() as session:
            chat = await get_or_create_chat(session, telegram_id=message.chat.id)
            from db.models import ChatMember as CM
            from sqlalchemy import select
            stmt = select(CM).where(CM.chat_id == chat.id)
            result = await session.execute(stmt)
            members = list(result.scalars().all())

        count = 0
        kicked = 0
        for member_record in members:
            try:
                tg_member = await message.bot.get_chat_member(
                    chat_id=message.chat.id,
                    user_id=member_record.user_id,
                )
                count += 1
                user = tg_member.user
                if user.is_bot:
                    continue
                # Deleted Telegram accounts have id = 777000 or no first_name
                if not user.first_name or user.id == 777000:
                    try:
                        await message.bot.ban_chat_member(
                            chat_id=message.chat.id,
                            user_id=user.id,
                        )
                        # Immediately unban so they can rejoin if they recover
                        await message.bot.unban_chat_member(
                            chat_id=message.chat.id,
                            user_id=user.id,
                        )
                        kicked += 1
                    except Exception:
                        pass
            except Exception:
                # User may have left or been banned already
                continue

        await status_msg.edit_text(
            f"✅ <b>Zombie cleanup complete!</b>\n"
            f"👥 Total members checked: {count}\n"
            f"🧟 Deleted accounts removed: {kicked}"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}. Make sure bot is admin!")
