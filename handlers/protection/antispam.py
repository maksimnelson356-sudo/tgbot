import asyncio
import logging
import time

from aiogram import Bot, Router, F
from aiogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
from db.base import async_session_factory
from db.queries import (
    add_chat_member,
    get_chat_member,
    get_or_create_chat,
    get_or_create_user,
    get_recent_joins,
    log_action,
    mute_member,
    set_invited_by,
)
from services.spam_detector import spam_detector
from utils.helpers import escape_html, schedule_delete, spawn

logger = logging.getLogger(__name__)

router = Router()
router.name = "antispam"

# In-memory raid tracking per chat
_raid_mode: dict[int, bool] = {}
_raid_timestamps: dict[int, float] = {}  # chat_id -> when raid was last activated

REFERRAL_XP_BONUS = 25


async def _tg_id_of(session, user_pk: int) -> int | None:
    """Resolve internal users.id → telegram_id."""
    from db.models import User
    row = await session.get(User, user_pk)
    return row.telegram_id if row else None


@router.chat_member()
async def on_chat_member_update(event: ChatMemberUpdated) -> None:
    """Handle new members joining the chat."""
    if event.new_chat_member.status not in ("member", "administrator"):
        return
    if event.old_chat_member.status == event.new_chat_member.status:
        return
    if event.chat is None:
        return

    new_user = event.new_chat_member.user
    if new_user.is_bot:
        return

    chat_id = event.chat.id
    user_id = new_user.id

    async with async_session_factory() as session:
        user = await get_or_create_user(
            session,
            telegram_id=user_id,
            username=new_user.username,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
        )
        chat = await get_or_create_chat(
            session,
            telegram_id=chat_id,
            title=getattr(event.chat, "title", None),
            chat_type=event.chat.type,
        )

        await add_chat_member(session, chat.id, user.id)
        await log_action(session, chat.id, user.id, "joined")

        # ── Invite attribution (G4): who invited this member? ────────────
        invite_link = getattr(event, "invite_link", None)
        if invite_link is not None:
            creator = getattr(invite_link, "creator", None)
            if creator is not None and not creator.is_bot and creator.id != user_id:
                inviter = await get_or_create_user(session, telegram_id=creator.id)
                await add_chat_member(session, chat.id, inviter.id)
                await set_invited_by(session, chat.id, user.id, inviter.id)

        # ── Referral credit (G4): first join after ref_<id> deep link ────
        from db.queries import add_xp, count_prior_joins, give_reputation
        if user.referred_by is not None:
            prior_joins = await count_prior_joins(session, chat_id, user_id)
            if prior_joins <= 1:  # the row we just logged is their first
                await give_reputation(session, chat.id, user.referred_by, user.id)
                await add_xp(session, chat.id, user.referred_by, REFERRAL_XP_BONUS)
                referrer_tg = await _tg_id_of(session, user.referred_by)
                new_name = escape_html(new_user.first_name or new_user.username or str(user_id))
                try:
                    if referrer_tg:
                        me = await event.bot.get_me()
                        await event.bot.send_message(
                            referrer_tg,
                            f"🎉 Твой друг <b>{new_name}</b> присоединился к группе!\n"
                            f"Бонус: +1 репутации и +{REFERRAL_XP_BONUS} XP в этом чате.\n"
                            f"Зови ещё — твоя ссылка: t.me/{me.username}?start=ref_{referrer_tg}",
                        )
                except Exception as e:
                    logger.debug("Referrer notify failed: %s", e)

        # Raid detection
        if chat.settings.get("raid_mode_enabled", True):
            recent_joins = await get_recent_joins(
                session, chat_id, settings.RAID_WINDOW
            )
            if recent_joins >= settings.RAID_JOIN_THRESHOLD:
                _raid_mode[chat_id] = True
                _raid_timestamps[chat_id] = time.time()

        # Welcome with action buttons (delayed, non-blocking)
        welcome_msg = chat.settings.get("welcome_message", "Добро пожаловать!")
        name = new_user.first_name or new_user.username or str(new_user.id)

        async def _send_welcome() -> None:
            await asyncio.sleep(20)
            try:
                sent = await event.bot.send_message(
                    chat_id,
                    f"👋 {escape_html(name)}, {escape_html(welcome_msg)}\n"
                    f"Осмотрись: правила, бонус дня и профиль — в кнопках:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="📜 Правила", callback_data="wl_rules"),
                        InlineKeyboardButton(text="🎁 Бонус", callback_data="wl_daily"),
                        InlineKeyboardButton(text="🏅 Профиль", callback_data="wl_rank"),
                    ]]),
                )
                # Buttons need interaction time — keep longer than 15s service TTL
                schedule_delete(sent, 120.0)
            except Exception as e:
                logger.warning("Welcome send failed in %s: %s", chat_id, e)

        spawn(_send_welcome(), name=f"welcome_{chat_id}_{user_id}")


@router.callback_query(F.data.in_({"wl_rules", "wl_daily", "wl_rank"}))
async def on_welcome_button(callback) -> None:
    """Handle welcome-message buttons."""
    from utils.helpers import get_user_mention

    if callback.message is None or callback.from_user.is_bot:
        return
    # Only the newcomer should drive their own welcome card
    if callback.message.reply_markup is None:
        return

    if callback.data == "wl_rules":
        async with async_session_factory() as session:
            chat = await get_or_create_chat(session, telegram_id=callback.message.chat.id)
        rules = (chat.settings or {}).get("rules") or (
            "Правила чата не заданы. Админы могут задать их командой /setrules."
        )
        try:
            await callback.message.answer(f"📜 <b>Правила:</b>\n\n{escape_html(rules)}")
        except Exception:
            pass
        await callback.answer()
    elif callback.data == "wl_daily":
        name = escape_html(callback.from_user.first_name or "")
        try:
            await callback.message.answer(
                f"🎁 {name}, жми команду /daily в чате — получи XP-бонус каждый день!"
            )
        except Exception:
            pass
        await callback.answer()
    else:
        mention = get_user_mention(callback.from_user)
        try:
            await callback.message.answer(
                f"🏅 {mention}, команда /rank покажет твой уровень, "
                f"/profile — профиль, /topxp — таблицу лидеров!"
            )
        except Exception:
            pass
        await callback.answer()


@router.message(F.new_chat_members)
async def on_new_members(message: Message) -> None:
    """Handle inline new_chat_members — delete the service join message only."""
    if message.new_chat_members is None:
        return

    # Delete the "X joined the group" service message
    try:
        await message.delete()
    except Exception:
        pass


@router.message(lambda msg: _raid_mode.get(msg.chat.id, False))
async def raid_mode_protection(message: Message) -> None:
    """When raid mode is active, restrict overly frequent messages."""
    if message.from_user is None:
        return

    # Auto-disable raid mode after cooldown
    chat_id = message.chat.id
    last_raid = _raid_timestamps.get(chat_id, 0)
    if time.time() - last_raid > 120:  # 2 min cooldown
        _raid_mode.pop(chat_id, None)
        return

    # Check spam score during raid
    result = spam_detector.check(message.text, message.from_user.id)
    if result.is_spam:
        try:
            await message.delete()
        except Exception:
            pass

        # Auto-mute during raid for heavy spam
        if result.score > 0.7:
            async with async_session_factory() as session:
                user = await get_or_create_user(
                    session, telegram_id=message.from_user.id
                )
                chat = await get_or_create_chat(
                    session, telegram_id=chat_id,
                )
                await mute_member(session, chat.id, user.id, 3600)
                await log_action(
                    session, chat.id, user.id,
                    "muted", details="Raid mode: high spam score",
                )


@router.message(F.left_chat_member)
async def on_left_member(message: Message) -> None:
    """Handle members leaving and auto-delete the service message."""
    if message.left_chat_member and not message.left_chat_member.is_bot:
        async with async_session_factory() as session:
            user = await get_or_create_user(
                session, telegram_id=message.left_chat_member.id,
            )
            chat = await get_or_create_chat(session, telegram_id=message.chat.id)
            await log_action(session, chat.id, user.id, "left")
    try:
        await message.delete()
    except Exception:
        pass


@router.my_chat_member()
async def on_bot_added(event: ChatMemberUpdated) -> None:
    """Set WebApp menu button when bot is added to a group."""
    if event.new_chat_member.status not in ("member", "administrator"):
        return
    if event.old_chat_member.status in ("member", "administrator"):
        return

    bot: Bot = event.bot
    # Note: setChatMenuButton only works in private chats (Telegram API limitation).
    # In groups, the menu button must be set via the user's private chat with the bot.
    logger.info("Bot added to chat: %s (%s)", event.chat.id, getattr(event.chat, "title", "?"))
