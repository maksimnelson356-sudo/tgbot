import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from filters.admin import HasRank
from filters.chat_type import IsGroup

logger = logging.getLogger(__name__)

router = Router()
router.name = "zombies"


@router.message(Command("zombies"), IsGroup(), HasRank(2))
async def cmd_zombies(message: Message) -> None:
    """Remove deleted/deactivated accounts using Telethon (full member list)."""
    from services.telethon_client import get_client

    status_msg = await message.answer("🔍 Запускаю сканирование... Это может занять время.")

    client = await get_client()
    if client is None:
        await status_msg.edit_text(
            "❌ Telethon не настроен.\n"
            "Добавь в `.env`:\n"
            "```\n"
            "TELETHON_API_ID=...\n"
            "TELETHON_API_HASH=...\n"
            "```\n"
            "Получи на https://my.telegram.org"
        )
        return

    try:
        chat = await client.get_entity(message.chat.id)

        count = 0
        kicked = 0
        skipped = 0

        async for user in client.iter_participants(chat, aggressive=False):
            count += 1

            if user.bot:
                skipped += 1
                continue

            # Deleted accounts: no first_name or id = 777000
            if not user.first_name or user.id == 777000:
                try:
                    await message.bot.ban_chat_member(
                        chat_id=message.chat.id,
                        user_id=user.id,
                    )
                    await message.bot.unban_chat_member(
                        chat_id=message.chat.id,
                        user_id=user.id,
                    )
                    kicked += 1
                except Exception:
                    pass

            # Update status every 500 members
            if count % 500 == 0:
                try:
                    await status_msg.edit_text(
                        f"🔍 Сканирование... {count} участников проверено, {kicked} удалено"
                    )
                except Exception:
                    pass

        await status_msg.edit_text(
            f"✅ <b>Zombie cleanup complete!</b>\n"
            f"👥 Total members checked: {count}\n"
            f"🤖 Bots skipped: {skipped}\n"
            f"🧟 Deleted accounts removed: {kicked}"
        )

    except Exception as e:
        logger.error("Zombies scan failed: %s", e)
        await status_msg.edit_text(f"❌ Ошибка: {e}")
