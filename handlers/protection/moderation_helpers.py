"""Shared moderation helper functions used by all moderation paths."""

import datetime
import logging

from aiogram.types import ChatPermissions

from db.queries import (
    add_warning,
    increment_warnings,
    log_action,
    mute_member,
    reset_warnings,
)
from utils.helpers import display_name
from utils.i18n import t

logger = logging.getLogger(__name__)


async def handle_warning(
    session, chat, user, message, reason, lang, settings
) -> None:
    """Apply warning + mute + log for a moderation violation.

    Shared by all three moderation paths (text, media, sticker).
    """
    await add_warning(session, chat.id, user.id, None, reason=reason)
    warn_count = await increment_warnings(session, chat.id, user.id)
    max_warnings = settings.get("max_warnings", 3)
    mention = display_name(message.from_user)

    if warn_count >= max_warnings:
        mute_duration = settings.get("mute_duration", 900)
        await mute_member(session, chat.id, user.id, mute_duration)
        try:
            until_date = datetime.datetime.now() + datetime.timedelta(seconds=mute_duration)
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
        except Exception as e:
            logger.warning("Failed to mute user %s: %s", message.from_user.id, e)
        await log_action(
            session, chat.id, user.id,
            "muted", details=f"Auto-mute: {warn_count}/{max_warnings} warnings",
        )
        await message.answer(t("mod_muted", lang, user=mention, count=warn_count, max=max_warnings, reason=reason))
        await reset_warnings(session, chat.id, user.id)
    else:
        await message.answer(t("mod_warned", lang, user=mention, count=warn_count, max=max_warnings, reason=reason))

    await log_action(
        session, chat.id, user.id,
        "warned", details=reason,
    )


async def handle_media_moderation(
    session, chat, user, message, reason, lang, settings
) -> None:
    """Delete the message and apply warning action for media moderation.

    Used by moderate_filtered_media and moderate_nsfw_media.
    """
    try:
        await message.delete()
    except Exception as e:
        logger.warning("Failed to delete media message: %s", e)

    await handle_warning(session, chat, user, message, reason, lang, settings)