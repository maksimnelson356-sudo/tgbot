from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.base import async_session_factory
from db.queries import add_chat_admin, get_or_create_chat, get_chat_admin_rank
from db.queries import list_chat_admins, remove_chat_admin, update_chat_settings
from db.queries import get_or_create_user, is_chat_admin_db
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.i18n import t
from utils.lang_helper import get_user_lang

PANEL_URL = "https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html"

router = Router()
router.name = "admin_panel"


# ── Helper: check effective admin (used for callback queries) ─────────────────

async def _check_admin_access(chat, user_id) -> bool:
    """Check if user is Telegram admin OR bot admin (any rank)."""
    try:
        member = await chat.get_member(user_id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception:
        pass
    async with async_session_factory() as session:
        chat_db = await get_or_create_chat(session, telegram_id=chat.id)
        user = await get_or_create_user(session, telegram_id=user_id)
        return await get_chat_admin_rank(session, chat_db.id, user.id) is not None


_RANK_NAMES = {1: "Младший", 2: "Администратор", 3: "Главный"}
_RANK_EMOJI = {1: "🔰", 2: "🛡️", 3: "👑"}


# ── /admin — Admin panel ──────────────────────────────────────────────────────

@router.message(Command("admin"), IsGroup(), HasRank(3))
async def cmd_admin(message: Message) -> None:
    """Show admin panel with inline buttons (groups only, rank 3+)."""
    if message.from_user is None:
        return

    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        chat = await get_or_create_chat(
            session, telegram_id=message.chat.id,
        )
        settings = chat.settings or {}

    statuses = []
    for key, label_key in [
        ("antispam_enabled", "admin_antispam"),
        ("moderation_enabled", "admin_moderation"),
        ("filter_links", "admin_links"),
        ("filter_media", "admin_media"),
        ("nsfw_filter_enabled", "admin_nsfw"),
        ("bad_words_enabled", "admin_badwords"),
        ("antiforward_enabled", "admin_antiforward"),
        ("antispam_contacts", "admin_contacts"),
        ("captcha_enabled", "admin_captcha"),
        ("raid_mode_enabled", "admin_raid"),
    ]:
        val = settings.get(key, True)
        status = t("on", lang) if val else t("off", lang)
        statuses.append(f"{t(label_key, lang)}: {status}")

    builder = _build_admin_kb(lang)
    await message.answer(
        t("admin_panel_title", lang, statuses="\n".join(statuses)),
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback(callback: CallbackQuery) -> None:
    """Handle admin panel button clicks."""
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    if callback.message.chat.type not in ("group", "supergroup"):
        await callback.answer("Not a group!")
        return
    if not await _check_admin_access(callback.message.chat, callback.from_user.id):
        await callback.answer("Admins only!")
        return

    action = callback.data.removeprefix("admin:")
    if action == "close":
        await callback.message.delete()
        await callback.answer()
        return

    key_map = {
        "toggle_antispam": "antispam_enabled",
        "toggle_moderation": "moderation_enabled",
        "toggle_links": "filter_links",
        "toggle_media": "filter_media",
        "toggle_nsfw": "nsfw_filter_enabled",
        "toggle_badwords": "bad_words_enabled",
        "toggle_antiforward": "antiforward_enabled",
        "toggle_contacts": "antispam_contacts",
        "toggle_captcha": "captcha_enabled",
        "toggle_raid": "raid_mode_enabled",
    }
    setting_key = key_map.get(action)
    if setting_key is None:
        await callback.answer("Unknown action")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=callback.message.chat.id)
        current = chat.settings.get(setting_key, True)
        await update_chat_settings(session, chat.id, {setting_key: not current})

    await callback.answer(f"Toggled {'ON' if not current else 'OFF'}")

    lang = await get_user_lang(callback)
    builder = _build_admin_kb(lang)

    async with async_session_factory() as session:
        updated = await get_or_create_chat(session, telegram_id=callback.message.chat.id)
        settings = updated.settings or {}

    statuses = []
    for key, label_key in [
        ("antispam_enabled", "admin_antispam"),
        ("moderation_enabled", "admin_moderation"),
        ("filter_links", "admin_links"),
        ("filter_media", "admin_media"),
        ("nsfw_filter_enabled", "admin_nsfw"),
        ("bad_words_enabled", "admin_badwords"),
        ("antiforward_enabled", "admin_antiforward"),
        ("antispam_contacts", "admin_contacts"),
        ("captcha_enabled", "admin_captcha"),
        ("raid_mode_enabled", "admin_raid"),
    ]:
        val = settings.get(key, True)
        status = t("on", lang) if val else t("off", lang)
        statuses.append(f"{t(label_key, lang)}: {status}")

    try:
        await callback.message.edit_text(
            t("admin_panel_title", lang, statuses="\n".join(statuses)),
            reply_markup=builder.as_markup(),
        )
    except Exception:
        pass


# ── /addadmin — Add bot admin with rank selection ─────────────────────────────

@router.message(Command("addadmin"), IsGroup(), HasRank(3))
async def cmd_addadmin(message: Message) -> None:
    """Add a user as bot admin. Reply to message with /addadmin or /addadmin 1/2/3."""
    if message.from_user is None:
        return

    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    elif message.text.strip():
        args = message.text.removeprefix("/addadmin").strip()
        if args.startswith("@"):
            username = args.split()[0].lstrip("@")
            async with async_session_factory() as session:
                from sqlalchemy import select
                from db.models import User as UserModel
                stmt = select(UserModel).where(UserModel.username == username)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    target_user = type("obj", (), {"id": row.telegram_id, "first_name": row.first_name or username})()

    if target_user is None:
        await message.answer("Ответь на сообщение пользователя: /addadmin [ранг 1/2/3]")
        return

    # Parse rank from args or default to 1
    args = (message.text.removeprefix("/addadmin").strip().split() or [])
    rank = 1
    for arg in args:
        if arg.isdigit() and 1 <= int(arg) <= 3:
            rank = int(arg)
            break

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        admin_user = await get_or_create_user(session, telegram_id=message.from_user.id)
        target = await get_or_create_user(session, telegram_id=target_user.id)
        await add_chat_admin(session, chat.id, target.id, admin_user.id, rank=rank)

    name = target_user.first_name or str(target_user.id)
    rank_label = f"{_RANK_EMOJI[rank]} {_RANK_NAMES[rank]}"
    await message.answer(f"✅ <b>{name}</b> назначен — {rank_label}")


# ── /removeadmin — Remove bot admin ───────────────────────────────────────────

@router.message(Command("removeadmin"), IsGroup(), HasRank(3))
async def cmd_removeadmin(message: Message) -> None:
    """Remove a bot admin. Reply to message."""
    if message.from_user is None:
        return

    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user

    if target_user is None:
        await message.answer("Ответь на сообщение пользователя: /removeadmin")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        target = await get_or_create_user(session, telegram_id=target_user.id)
        removed = await remove_chat_admin(session, chat.id, target.id)

    if not removed:
        await message.answer("❌ Этот пользователь не администратор бота.")
        return

    name = target_user.first_name or str(target_user.id)
    await message.answer(f"✅ <b>{name}</b> понижен — больше не администратор.")


# ── /adminlist — Show bot admins ──────────────────────────────────────────────

@router.message(Command("adminlist"), IsGroup())
async def cmd_adminlist(message: Message) -> None:
    """Show all bot-level admins with ranks."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        admins = await list_chat_admins(session, chat.id)

    if not admins:
        await message.answer("📋 Нет назначенных администраторов бота.")
        return

    lines = ["📋 <b>Администраторы бота:</b>"]
    for user, rank in admins:
        name = f"@{user.username}" if user.username else f"<b>{user.first_name or 'Unknown'}</b>"
        rank_label = f"{_RANK_EMOJI.get(rank, '❓')} {_RANK_NAMES.get(rank, 'Неизвестно')}"
        lines.append(f"• {name} — {rank_label}")
    await message.answer("\n".join(lines))


# ── "Повысить" / "Понизить" / "Кто админ" — text commands ────────────────────

@router.message(F.text.in_({"Повысить", "повысить", "ПОВЫСИТЬ"}), F.reply_to_message, IsGroup(), HasRank(3))
async def text_addadmin(message: Message) -> None:
    """Reply with 'Повысить' to promote a user by one rank (max 3)."""
    target = message.reply_to_message.from_user
    if target is None or target.is_bot:
        await message.answer("Нельзя назначить бота.")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        admin_user = await get_or_create_user(session, telegram_id=message.from_user.id)
        target_user = await get_or_create_user(session, telegram_id=target.id)
        current_rank = await get_chat_admin_rank(session, chat.id, target_user.id) or 0
        new_rank = min(current_rank + 1, 3)
        await add_chat_admin(session, chat.id, target_user.id, admin_user.id, rank=new_rank)

    name = target.first_name or str(target.id)
    rank_label = f"{_RANK_EMOJI[new_rank]} {_RANK_NAMES[new_rank]}"
    await message.answer(f"✅ <b>{name}</b> назначен — {rank_label}")


@router.message(F.text.in_({"Понизить", "понизить", "ПОНИЗИТЬ"}), F.reply_to_message, IsGroup(), HasRank(3))
async def text_removeadmin(message: Message) -> None:
    """Reply with 'Понизить' to demote a user."""
    target = message.reply_to_message.from_user
    if target is None:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        target_user = await get_or_create_user(session, telegram_id=target.id)
        removed = await remove_chat_admin(session, chat.id, target_user.id)

    name = target.first_name or str(target.id)
    if removed:
        await message.answer(f"✅ <b>{name}</b> понижен — больше не администратор.")
    else:
        await message.answer(f"❌ <b>{name}</b> не был администратором.")


@router.message(
    F.text.in_({"Кто админ", "кто админ", "КТО АДМИН", "Кто админы", "кто админы", "Админы", "админы"}),
    IsGroup(),
)
async def text_wloadmins(message: Message) -> None:
    """Show admin list by text command."""
    await cmd_adminlist(message)


# ── Admin keyboard builder ────────────────────────────────────────────────────

def _build_admin_kb(lang: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("admin_antispam", lang), callback_data="admin:toggle_antispam")
    builder.button(text=t("admin_moderation", lang), callback_data="admin:toggle_moderation")
    builder.button(text=t("admin_links", lang), callback_data="admin:toggle_links")
    builder.button(text=t("admin_media", lang), callback_data="admin:toggle_media")
    builder.button(text=t("admin_nsfw", lang), callback_data="admin:toggle_nsfw")
    builder.button(text=t("admin_badwords", lang), callback_data="admin:toggle_badwords")
    builder.button(text=t("admin_captcha", lang), callback_data="admin:toggle_captcha")
    builder.button(text=t("admin_raid", lang), callback_data="admin:toggle_raid")
    builder.button(text=t("admin_close", lang), callback_data="admin:close")
    builder.adjust(2)
    return builder


# ── /panel — WebApp admin panel ─────────────────────────────────────────────

@router.message(Command("panel"), IsGroup(), HasRank(3))
async def cmd_panel(message: Message) -> None:
    """Set WebApp menu button for this group."""
    PANEL_URL = "https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html"
    from aiogram.types import MenuButtonWebApp, WebAppInfo
    try:
        await message.bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="⚙️ Панель", web_app=WebAppInfo(url=PANEL_URL)),
        )
        await message.answer("✅ Кнопка меню установлена! Обнови чат и нажми Menu внизу.")
    except Exception as e:
        logger.warning("set_chat_menu_button failed for group %s: %s", message.chat.id, e)
        # Fallback: send WebApp link to user's DM
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="⚙️ Открыть панель",
                web_app=WebAppInfo(url=f"{PANEL_URL}?chat_id={message.chat.id}"),
            )
        ]])
        try:
            await message.bot.send_message(
                chat_id=message.from_user.id,
                text=f"⚙️ Панель управления — {message.chat.title or 'группа'}",
                reply_markup=kb,
            )
            await message.answer("✅ Панель отправлена в личные сообщения.")
        except Exception:
            await message.answer("❌ Не удалось. Напиши боту /start в ЛС.")


@router.message(Command("panel"), F.chat.type == "private")
async def cmd_panel_dm(message: Message) -> None:
    """Show groups list with WebApp buttons (in DM)."""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        from db.queries import get_user_admin_chats, get_or_create_user
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        admin_chats = await get_user_admin_chats(session, message.from_user.id)

    if not admin_chats:
        await message.answer(t("panel_no_groups", lang))
        return

    buttons = []
    for chat in admin_chats:
        title = chat.title or f"Chat {chat.telegram_id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"⚙️ {title}",
                web_app=WebAppInfo(url=f"{PANEL_URL}?chat_id={chat.telegram_id}"),
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(t("panel_dm_title", lang), reply_markup=kb)
