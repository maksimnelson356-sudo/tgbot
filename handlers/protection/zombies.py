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

BATCH_SIZE = 200


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
        offset = 0

        while True:
            try:
                participants = await client.get_participants(
                    chat, limit=BATCH_SIZE, offset=offset
                )
            except Exception as e:
                logger.warning("Telethon batch error at offset %d: %s", offset, e)
                await asyncio.sleep(5)
                try:
                    participants = await client.get_participants(
                        chat, limit=BATCH_SIZE, offset=offset
                    )
                except Exception:
                    errors += 1
                    break

            if not participants:
                break

            for user in participants:
                count += 1

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
                    continue

                # Abandoned: no profile photo
                if user.photo is None:
                    abandoned += 1

            offset += len(participants)

            # Update status every batch
            try:
                await status_msg.edit_text(
                    f"🔍 Проверено {count} участников...\n"
                    f"🧟 Удалённых: {deleted} | Заброшенных: {abandoned}"
                )
            except Exception:
                pass

            # Small delay between batches to avoid flood
            await asyncio.sleep(1)

        await asyncio.sleep(3)

        lines = [
            "✅ <b>Zombie cleanup complete!</b>",
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
