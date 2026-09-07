from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, set_chat_setting
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.helpers import escape_html, keep_next
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "rules"


@router.message(Command("rules"), IsGroup())
async def cmd_rules(message: Message) -> None:
    """Show chat rules."""
    lang = await get_user_lang(message)
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        rules = (chat.settings or {}).get("rules", "")

    if not rules:
        await message.answer("📜 Правила не установлены. Админы могут использовать /setrules <текст>")
        return

    keep_next(message)
    await message.answer(f"📜 <b>Правила</b>\n\n{escape_html(rules)}")


@router.message(Command("setrules"), IsGroup(), HasRank(2))
async def cmd_setrules(message: Message) -> None:
    """Set chat rules. Usage: /setrules <text>"""
    text = message.text.removeprefix("/setrules").strip()
    if not text:
        await message.answer("Использование: /setrules <текст правил>")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await set_chat_setting(session, chat.id, "rules", text)

    await message.answer("✅ Правила обновлены!")


@router.message(Command("delrules"), IsGroup(), HasRank(2))
async def cmd_delrules(message: Message) -> None:
    """Delete chat rules."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await set_chat_setting(session, chat.id, "rules", "")

    await message.answer("✅ Правила удалены.")
