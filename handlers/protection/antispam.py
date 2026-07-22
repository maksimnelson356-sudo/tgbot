import asyncio
import logging
import time

from aiogram import Bot, Router, F
from aiogram.types import ChatMemberUpdated, Message

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
)
from services.spam_detector import spam_detector

logger = logging.getLogger(__name__)

router = Router()
router.name = "antispam"

# In-memory raid tracking per chat
_raid_mode: dict[int, bool] = {}
_raid_timestamps: dict[int, float] = {}  # chat_id -> when raid was last activated


async def _delete_after(message: Message, delay: float = 3.0) -> None:
    """Delete a message after a delay."""
    from utils.helpers import delete_after as _da
    await _da(message, delay)


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
        await log_action(session, chat_id, user_id, "joined")

        # Raid detection
        if chat.settings.get("raid_mode_enabled", True):
            recent_joins = await get_recent_joins(
                session, chat_id, settings.RAID_WINDOW
            )
            if recent_joins >= settings.RAID_JOIN_THRESHOLD:
                _raid_mode[chat_id] = True
                _raid_timestamps[chat_id] = time.time()

        # Welcome
        welcome_msg = chat.settings.get("welcome_message", "Добро пожаловать!")
        name = new_user.first_name or new_user.username or str(new_user.id)
        try:
            sent = await event.bot.send_message(chat_id, f"👋 {name}, {welcome_msg}")
            asyncio.create_task(_delete_after(sent, 3.0))
        except Exception:
            pass


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
                    session, chat_id, message.from_user.id,
                    "muted", details="Raid mode: high spam score",
                )


@router.message(F.left_chat_member)
async def on_left_member(message: Message) -> None:
    """Handle members leaving and auto-delete the service message."""
    if message.left_chat_member and not message.left_chat_member.is_bot:
        async with async_session_factory() as session:
            await log_action(session, message.chat.id, message.left_chat_member.id, "left")
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
