import asyncio
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
    """Scan all members for deleted and abandoned accounts using Telethon."""
    from services.telethon_client import get_client

    status_msg = await message.answer("🔍 Сканирую всех участников... Это займёт время.")

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
        deleted = 0
        abandoned = 0
        bots = 0
        errors = 0

        # iter_participants auto-paginates through ALL members (>200 too)
        async for user in client.iter_participants(chat):
            count += 1

            if count % 200 == 0:
                try:
                    await status_msg.edit_text(
                        f"🔍 Проверено {count} участников...\n"
                        f"🧟 Удалённых: {deleted} | Заброшенных: {abandoned}"
                    )
                except Exception:
                    pass
                await asyncio.sleep(1)

            if user.bot:
                bots += 1
                continue

            # Deleted accounts
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
                    deleted += 1
                except Exception:
                    errors += 1
                    await asyncio.sleep(1)
                continue

            # Abandoned: no profile photo
            if user.photo is None:
                abandoned += 1

        await asyncio.sleep(3)

        lines = [
            "✅ <b>Очистка завершена!</b>",
            f"👥 Всего участников: {count}",
            f"🤖 Ботов: {bots}",
            f"🧟 Удалённых аккаунтов: {deleted}",
            f"👻 Заброшенных (без фото): {abandoned}",
        ]
        if errors:
            lines.append(f"⚠️ Ошибок: {errors}")

        await status_msg.edit_text("\n".join(lines))

    except Exception as e:
        logger.error("Zombies scan failed: %s", e)
        await status_msg.edit_text(f"❌ Ошибка: {e}")
