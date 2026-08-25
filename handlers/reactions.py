"""Reaction-based reputation: 👍 on a message gives +1 rep."""
import datetime
import logging

from aiogram import Router
from aiogram.types import Update, ReactionTypeEmoji

from db.base import async_session_factory
from db.queries import (
    count_rep_given_today,
    get_last_rep_given_at,
    get_or_create_chat,
    get_or_create_user,
    give_reputation,
)

router = Router()
router.name = "reactions"

logger = logging.getLogger(__name__)

# Short anti-spam cooldown per (chat, reactor, message)
_cooldowns: dict[tuple[int, int, int], float] = {}
_COOLDOWN_SEC = 10

RATE_COOLDOWN = 30 * 60      # same pair-cooldown as /rate
DAILY_REP_LIMIT = 10         # same daily cap as /rate

# Positive reaction emoji -> +rep
_POSITIVE_EMOJIS = {"👍", "❤️", "🔥", "👏", "💯", "⭐"}


def _positive_emojis(update_reaction) -> set[str]:
    """Extract positive emoji set from old/new reaction payload."""
    out: set[str] = set()
    for r in update_reaction or []:
        if isinstance(r, ReactionTypeEmoji) and r.emoji in _POSITIVE_EMOJIS:
            out.add(r.emoji)
    return out


async def on_reaction(update: Update) -> None:
    """Handle message reactions (called from dispatcher update listener)."""
    import time

    reaction = update.message_reaction
    if not reaction or not reaction.user:
        return
    reactor = reaction.user
    if reactor.is_bot:
        return

    # Only react to ADDED positive reactions: emoji present in new state
    # and absent from the old one. Removing a reaction never grants rep.
    added = _positive_emojis(reaction.new_reaction) - _positive_emojis(reaction.old_reaction)
    if not added:
        return

    msg_id = reaction.message_id
    chat_id = reaction.chat.id

    # Anti-spam cooldown per message
    now = time.monotonic()
    key = (chat_id, reactor.id, msg_id)
    if now - _cooldowns.get(key, 0) < _COOLDOWN_SEC:
        return
    _cooldowns[key] = now

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

            # Anti-farm #1: pair cooldown persisted in DB (survives restarts).
            last = await get_last_rep_given_at(session, chat.id, target_user.id, reactor_user.id)
            if last is not None:
                elapsed = (datetime.datetime.now() - last).total_seconds()
                if elapsed < RATE_COOLDOWN:
                    return

            # Anti-farm #2: daily cap per giver.
            given_today = await count_rep_given_today(session, chat.id, reactor_user.id)
            if given_today >= DAILY_REP_LIMIT:
                return

            total = await give_reputation(session, chat.id, target_user.id, reactor_user.id)

            logger.info(
                "Reaction rep: %s -> %s in chat %s (total: %d)",
                reactor.first_name or "Someone",
                target_user.first_name or "User",
                chat_id, total,
            )
    except Exception as e:
        logger.warning("Reaction rep failed: %s", e)
