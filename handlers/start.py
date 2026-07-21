from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "start"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    if message.from_user is None:
        return

    lang = await get_user_lang(message)

    # Save/update user in DB
    async with async_session_factory() as session:
        await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

    welcome_text = t("start_welcome", lang, name=message.from_user.first_name)
    await message.answer(welcome_text)


@router.message(Command("help", "menu"))
async def cmd_help(message: Message) -> None:
    """Handle /help and /menu commands."""
    await cmd_start(message)
