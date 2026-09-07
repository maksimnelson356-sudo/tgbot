import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.base import async_session_factory
from db.queries import add_chat_admin, get_or_create_chat, get_chat_admin_rank
from db.queries import list_chat_admins, remove_chat_admin, set_chat_setting
from db.queries import get_or_create_user, is_chat_admin_db
from db.models import ActionLog
from sqlalchemy import select, func
import datetime
from filters.admin import HasRank
from filters.chat_type import IsGroup, IsReplyTo
from utils.helpers import display_name, escape_html, keep_next, spawn
from utils.i18n import t
from utils.lang_helper import get_user_lang

logger = logging.getLogger(__name__)

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
        ("raid_mode_enabled", "admin_raid"),
        ("ai_chat_enabled", "admin_ai_chat"),
    ]:
        val = settings.get(key, True)
        status = t("on", lang) if val else t("off", lang)
        statuses.append(f"{t(label_key, lang)}: {status}")

    builder = _build_admin_kb(lang)
    panel_msg = await message.answer(
        t("admin_panel_title", lang, statuses="\n".join(statuses)),
        reply_markup=builder.as_markup(),
    )

    async def _delete_later():
        await asyncio.sleep(120)
        try:
            await panel_msg.delete()
        except Exception:
            pass
    spawn(_delete_later(), name="admin_panel_hide")


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
        "toggle_raid": "raid_mode_enabled",
        "toggle_ai_chat": "ai_chat_enabled",
    }
    setting_key = key_map.get(action)
    if setting_key is None:
        await callback.answer("Unknown action")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=callback.message.chat.id)
        current = chat.settings.get(setting_key, True)
        await set_chat_setting(session, chat.id, setting_key, not current)

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
        ("raid_mode_enabled", "admin_raid"),
        ("ai_chat_enabled", "admin_ai_chat"),
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

    name = escape_html(target_user.first_name or str(target_user.id))
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

    name = escape_html(target_user.first_name or str(target_user.id))
    await message.answer(f"✅ <b>{name}</b> понижен — больше не администратор.")


# ── /adminlist — Show bot admins ──────────────────────────────────────────────

@router.message(Command("adminlist"), IsGroup(), HasRank(1))
async def cmd_adminlist(message: Message) -> None:
    """Show all bot-level admins with ranks (bot admins only)."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        admins = await list_chat_admins(session, chat.id)

    if not admins:
        await message.answer("📋 Нет назначенных администраторов бота.")
        return

    lines = ["📋 <b>Администраторы бота:</b>"]
    for user, rank in admins:
        name = display_name(user, default="Unknown")
        rank_label = f"{_RANK_EMOJI.get(rank, '❓')} {_RANK_NAMES.get(rank, 'Неизвестно')}"
        lines.append(f"• {name} — {rank_label}")
    keep_next(message)
    await message.answer("\n".join(lines))


# ── "Повысить" / "Понизить" / "Кто админ" — text commands ────────────────────

@router.message(F.text.in_({"Повысить", "повысить", "ПОВЫСИТЬ"}), IsReplyTo(), IsGroup(), HasRank(3))
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

    name = escape_html(target.first_name or str(target.id))
    rank_label = f"{_RANK_EMOJI[new_rank]} {_RANK_NAMES[new_rank]}"
    await message.answer(f"✅ <b>{name}</b> назначен — {rank_label}")


@router.message(F.text.in_({"Понизить", "понизить", "ПОНИЗИТЬ"}), IsReplyTo(), IsGroup(), HasRank(3))
async def text_removeadmin(message: Message) -> None:
    """Reply with 'Понизить' to demote a user."""
    target = message.reply_to_message.from_user
    if target is None:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        target_user = await get_or_create_user(session, telegram_id=target.id)
        removed = await remove_chat_admin(session, chat.id, target_user.id)

    name = escape_html(target.first_name or str(target.id))
    if removed:
        await message.answer(f"✅ <b>{name}</b> понижен — больше не администратор.")
    else:
        await message.answer(f"❌ <b>{name}</b> не был администратором.")


@router.message(
    F.text.in_({"Кто админ", "кто админ", "КТО АДМИН", "Кто админы", "кто админы", "Админы", "админы"}),
    IsGroup(),
    HasRank(1),
)
async def text_wloadmins(message: Message) -> None:
    """Show admin list by text command (bot admins rank 1+ or Telegram admins)."""
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
    builder.button(text=t("admin_antiforward", lang), callback_data="admin:toggle_antiforward")
    builder.button(text=t("admin_contacts", lang), callback_data="admin:toggle_contacts")
    builder.button(text=t("admin_raid", lang), callback_data="admin:toggle_raid")
    builder.button(text=t("admin_ai_chat", lang), callback_data="admin:toggle_ai_chat")
    builder.button(text=t("admin_close", lang), callback_data="admin:close")
    builder.adjust(2)
    return builder


# ── /panel — WebApp admin panel ─────────────────────────────────────────────

@router.message(Command("panel"), IsGroup(), HasRank(3))
async def cmd_panel(message: Message) -> None:
    """Send WebApp panel button to user's DM."""
    PANEL_URL = "https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html"
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        settings = chat.settings or {}

    params = "&".join(f"{k}={1 if v else 0}" for k, v in settings.items() if isinstance(v, bool))
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"⚙️ {message.chat.title or 'Группа'}",
            web_app=WebAppInfo(url=f"{PANEL_URL}?chat_id={message.chat.id}&{params}"),
        )
    ]])
    try:
        await message.bot.send_message(
            chat_id=message.from_user.id,
            text=f"⚙️ Панель управления — <b>{message.chat.title or 'группа'}</b>",
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
    for chat_item in admin_chats:
        title = chat_item.title or f"Chat {chat_item.telegram_id}"
        chat_settings = chat_item.settings or {}
        params = "&".join(f"{k}={1 if v else 0}" for k, v in chat_settings.items() if isinstance(v, bool))
        buttons.append([
            InlineKeyboardButton(
                text=f"⚙️ {title}",
                web_app=WebAppInfo(url=f"{PANEL_URL}?chat_id={chat_item.telegram_id}&{params}"),
            )
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(t("panel_dm_title", lang), reply_markup=kb)


# ── /logs — Action log dashboard ─────────────────────────────────────────────

_LOGS_PER_PAGE = 10

# In-memory pagination state: {chat_id: {"action_type": str, "days": int, "page": int}}
_logs_state: dict[int, dict] = {}


@router.message(Command("logs"), IsGroup(), HasRank(2))
async def cmd_logs(message: Message) -> None:
    """Show action logs with optional filters: /logs [action_type] [days] [page]"""
    if message.from_user is None:
        return

    args = message.text.removeprefix("/logs").strip().split()
    action_type = None
    days = 7
    page = 0

    for arg in args:
        if arg.isdigit():
            if action_type is None and not arg.startswith("0"):
                # Could be page or days — treat as days if <= 365
                val = int(arg)
                if val <= 365:
                    days = val
                else:
                    page = max(0, (val // _LOGS_PER_PAGE) - 1)
        elif arg.isalpha():
            action_type = arg.lower()

    # Save state for pagination
    _logs_state[message.chat.id] = {
        "action_type": action_type,
        "days": days,
        "page": page,
    }

    await _render_logs_page(message, action_type, days, page)


async def _render_logs_page(message: Message, action_type: str | None, days: int, page: int) -> None:
    """Fetch and render one page of logs."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)

    async with async_session_factory() as session:
        stmt = select(ActionLog).where(ActionLog.chat_id == message.chat.id, ActionLog.created_at >= cutoff)
        if action_type:
            stmt = stmt.where(ActionLog.action_type == action_type)
        stmt = stmt.order_by(ActionLog.created_at.desc()).offset(page * _LOGS_PER_PAGE).limit(_LOGS_PER_PAGE)
        result = await session.execute(stmt)
        logs = list(result.scalars().all())

        # Count total for pagination
        count_stmt = select(func.count(ActionLog.id)).where(ActionLog.chat_id == message.chat.id, ActionLog.created_at >= cutoff)
        if action_type:
            count_stmt = count_stmt.where(ActionLog.action_type == action_type)
        total = (await session.execute(count_stmt)).scalar() or 0

    if not logs:
        await message.answer(f"📋 Логов за {days} дн. не найдено.")
        return

    total_pages = max(1, (total + _LOGS_PER_PAGE - 1) // _LOGS_PER_PAGE)

    action_labels = {
        "warned": "⚠️ Предупреждение",
        "muted": "🔇 Мут",
        "unmuted": "🔊 Размут",
        "banned": "🚫 Бан",
        "unbanned": "✅ Разбан",
        "joined": "👋 Вход",
        "left": "🚪 Выход",
        "deleted": "🗑 Удаление",
    }

    lines = [f"📋 <b>Логи</b> (стр. {page + 1}/{total_pages}, за {days} дн.):"]
    for log in logs:
        label = action_labels.get(log.action_type, log.action_type)
        ts = log.created_at.strftime("%d.%m %H:%M") if log.created_at else "?"
        user_ref = f"<code>{log.user_id}</code>"
        admin_ref = f" (админ: <code>{log.admin_id}</code>)" if log.admin_id else ""
        detail = f" — {log.details}" if log.details else ""
        lines.append(f"• {ts} {label} → {user_ref}{admin_ref}{detail}")

    await message.answer("\n".join(lines))


@router.message(Command("logs_prev"), IsGroup(), HasRank(2))
async def cmd_logs_prev(message: Message) -> None:
    """Go to previous page of logs."""
    state = _logs_state.get(message.chat.id)
    if state and state["page"] > 0:
        state["page"] -= 1
        await _render_logs_page(message, state["action_type"], state["days"], state["page"])
    else:
        await message.answer("📋 Это первая страница.")


@router.message(Command("logs_next"), IsGroup(), HasRank(2))
async def cmd_logs_next(message: Message) -> None:
    """Go to next page of logs."""
    state = _logs_state.get(message.chat.id)
    if state is None:
        await message.answer("Сначала вызови /logs")
        return
    state["page"] += 1
    await _render_logs_page(message, state["action_type"], state["days"], state["page"])


# ── /addword /delword — Bad word list management ─────────────────────────────

@router.message(Command("addword"), IsGroup(), HasRank(2))
async def cmd_addword(message: Message) -> None:
    """Add a word to the bad-words list. /addword <word>"""
    word = message.text.removeprefix("/addword").strip().lower()
    if not word:
        await message.answer("Использование: /addword <слово>")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        settings = chat.settings or {}
        bad_words = list(settings.get("bad_words", []))
        if word in bad_words:
            await message.answer(f"⚠️ Слово «{word}» уже в списке.")
            return
        bad_words.append(word)
        await set_chat_setting(session, chat.id, "bad_words", bad_words)

    await message.answer(f"✅ Слово «<b>{escape_html(word)}</b>» добавлено в чёрный список.")


@router.message(Command("delword"), IsGroup(), HasRank(2))
async def cmd_delword(message: Message) -> None:
    """Remove a word from the bad-words list. /delword <word>"""
    word = message.text.removeprefix("/delword").strip().lower()
    if not word:
        await message.answer("Использование: /delword <слово>")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        settings = chat.settings or {}
        bad_words = list(settings.get("bad_words", []))
        if word not in bad_words:
            await message.answer(f"⚠️ Слова «{word}» нет в списке.")
            return
        bad_words.remove(word)
        await set_chat_setting(session, chat.id, "bad_words", bad_words)

    await message.answer(f"✅ Слово «<b>{escape_html(word)}</b>» удалено из чёрного списка.")


@router.message(Command("badwords"), IsGroup(), HasRank(1))
async def cmd_badwords(message: Message) -> None:
    """List current bad words for this chat."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        bad_words = (chat.settings or {}).get("bad_words", [])

    if not bad_words:
        await message.answer("📝 Чёрный список пуст.")
        return
    lines = [f"📝 <b>Чёрный список ({len(bad_words)}):</b>"]
    for i, w in enumerate(bad_words, 1):
        lines.append(f"{i}. {escape_html(w)}")
    await message.answer("\n".join(lines))


# ── /banhistory — Ban history for a user ──────────────────────────────────────

@router.message(Command("banhistory"), IsGroup(), HasRank(2))
async def cmd_banhistory(message: Message) -> None:
    """Show ban history for a user. /banhistory [reply or @username]"""
    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    else:
        args = message.text.removeprefix("/banhistory").strip()
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
        await message.answer("Ответь на сообщение пользователя или укажи @username:\n/banhistory [@username]")
        return

    async with async_session_factory() as session:
        from db.models import ActionLog as AL
        stmt = (
            select(AL)
            .where(AL.user_id == target_user.id, AL.action_type == "banned")
            .order_by(AL.created_at.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        bans = list(result.scalars().all())

    if not bans:
        await message.answer(f"📋 Нет записей о банах для <code>{target_user.id}</code>.")
        return

    lines = [f"📋 <b>История банов</b> — <code>{target_user.id}</code>:"]
    for b in bans:
        ts = b.created_at.strftime("%d.%m.%Y %H:%M") if b.created_at else "?"
        admin_ref = f"админ: <code>{b.admin_id}</code>" if b.admin_id else "система"
        detail = f" — {b.details}" if b.details else ""
        lines.append(f"• {ts} | {admin_ref}{detail}")

    await message.answer("\n".join(lines))


# ── /setantispam /setslowmode — Anti-spam config commands ─────────────────────

@router.message(Command("setantispam"), IsGroup(), HasRank(2))
async def cmd_setantispam(message: Message) -> None:
    """Toggle antispam on/off. /setantispam on|off"""
    args = message.text.removeprefix("/setantispam").strip().lower()
    if args not in ("on", "off", "вкл", "выкл"):
        await message.answer("Использование: /setantispam on|off")
        return

    enabled = args in ("on", "вкл")

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await set_chat_setting(session, chat.id, "antispam_enabled", enabled)

    status = "включён" if enabled else "выключен"
    await message.answer(f"✅ Антиспам {status}.")


@router.message(Command("setslowmode"), IsGroup(), HasRank(2))
async def cmd_setslowmode(message: Message) -> None:
    """Set slow mode delay in seconds. /setslowmode <seconds> (0 to disable)"""
    args = message.text.removeprefix("/setslowmode").strip()
    if not args.isdigit() or int(args) < 0 or int(args) > 300:
        await message.answer("Использование: /setslowmode <секунды> (0-300, 0 = выключить)")
        return

    delay = int(args)

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await set_chat_setting(session, chat.id, "slowmode_delay", delay)

    if delay == 0:
        await message.answer("✅ Медленный режим выключен.")
    else:
        await message.answer(f"✅ Медленный режим: <b>{delay} сек.</b>")
