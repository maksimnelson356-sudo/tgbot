from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message, MenuButtonWebApp, WebAppInfo

from config import settings
from db.base import async_session_factory
from db.queries import get_or_create_user
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "start"

PANEL_URL = "https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html"


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject | None = None) -> None:
    """Handle /start command (incl. referral deep links /start ref_<id>)."""
    if message.from_user is None:
        return

    lang = await get_user_lang(message)

    # Save/update user in DB
    async with async_session_factory() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Referral payload: /start ref_<telegram_id>
        if command and command.args:
            from db.queries import set_referred_by
            arg = command.args.strip()
            if arg.startswith("ref_") and arg[4:].isdigit():
                referrer_tg_id = int(arg[4:])
                if referrer_tg_id != message.from_user.id:
                    credited = await set_referred_by(session, user.id, referrer_tg_id)
                    if credited:
                        await message.answer(
                            "🎁 Приглашение засчитано! Как только ты зайдёшь в группу, "
                            "друг получит бонус репутации."
                        )

    # Set menu button for this private chat (shows "Open App" on bot profile)
    try:
        await message.bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(
                text="⚙️ Панель",
                web_app=WebAppInfo(url=PANEL_URL),
            ),
        )
    except Exception:
        pass

    welcome_text = t("start_welcome", lang, name=message.from_user.first_name)
    await message.answer(welcome_text)


@router.message(Command("help", "menu"))
async def cmd_help(message: Message) -> None:
    """Handle /help and /menu commands."""
    await cmd_start(message)
