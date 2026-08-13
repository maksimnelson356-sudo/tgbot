"""Reaction-based reputation: 👍 on a message gives +1 rep."""
import logging
import time

from aiogram import Router
from aiogram.types import Update, ReactionTypeEmoji

from db.base import async_session_factory
from db.queries import get_or_create_chat, get_or_create_user, give_reputation

router = Router()
router.name = "reactions"

logger = logging.getLogger(__name__)

# Cooldown: (chat_id, reactor_id, target_msg_id) -> timestamp
_cooldowns: dict[tuple, float] = {}
_COOLDOWN_SEC = 10

# Positive reaction emoji -> +rep
_POSITIVE_EMOJIS = {"👍", "❤️", "🔥", "👏", "💯", "⭐"}


async def on_reaction(update: Update) -> None:
    """Handle message reactions (called from dispatcher update listener)."""
    reaction = update.message_reaction
    if not reaction or not reaction.new_reaction or not reaction.user:
        return

    reactor = reaction.user
    if reactor.is_bot:
        return

    msg_id = reaction.message_id
    chat_id = reaction.chat.id

    # Check cooldown
    now = time.monotonic()
    key = (chat_id, reactor.id, msg_id)
    if now - _cooldowns.get(key, 0) < _COOLDOWN_SEC:
        return
    _cooldowns[key] = now

    # Check if any positive reaction was added
    positive_added = False
    for r in reaction.new_reaction:
        if isinstance(r, ReactionTypeEmoji) and r.emoji in _POSITIVE_EMOJIS:
            positive_added = True
            break

    if not positive_added:
        return

    # Find the message author — we need to look it up from message_log
    try:
        from db.models import MessageLog
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = select(MessageLog.user_id).where(
                MessageLog.chat_id == chat_id,
                MessageLog.message_id == msg_id,
            )
            result = await session.execute(stmt)
            row = result.first()
            if not row:
                return
            target_telegram_id = row[0]

            # Don't self-rep
            if target_telegram_id == reactor.id:
                return

            target_user = await get_or_create_user(session, telegram_id=target_telegram_id)
            reactor_user = await get_or_create_user(session, telegram_id=reactor.id)
            chat = await get_or_create_chat(session, telegram_id=chat_id)

            total = await give_reputation(session, chat.id, target_user.id, reactor_user.id)

            name = reactor.first_name or "Someone"
            target_name = target_user.first_name or "User"
            logger.info(
                "Reaction rep: %s -> %s in chat %s (total: %d)",
                name, target_name, chat_id, total,
            )
    except Exception as e:
        logger.warning("Reaction rep failed: %s", e)
