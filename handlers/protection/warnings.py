import re

import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

from db.base import async_session_factory
from db.queries import (
    add_warning,
    get_chat_member,
    get_or_create_chat,
    get_or_create_user,
    get_user_warnings,
    increment_warnings,
    log_action,
    mute_member,
    reset_warnings,
    unmute_member,
)
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.i18n import t
from utils.lang_helper import get_user_lang
from utils.helpers import get_user_mention

router = Router()
router.name = "warnings"

_DURATION_RE = re.compile(r"(\d+)\s*(m|min|h|hour|d|day|s|sec)?", re.IGNORECASE)


def _parse_duration(text: str) -> int:
    match = _DURATION_RE.match(text)
    if not match:
        return 3600
    amount = int(match.group(1))
    unit = match.group(2)
    if unit and unit.lower() in ("s", "sec"):
        return amount
    if unit and unit.lower() in ("m", "min"):
        return amount * 60
    if unit and unit.lower() in ("h", "hour"):
        return amount * 3600
    if unit and unit.lower() in ("d", "day"):
        return amount * 86400
    return amount * 60


def _format_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    if seconds >= 3600:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        return f"{seconds // 60}min"
    return f"{seconds}s"


async def _do_warn(message: Message, reason: str = "No reason provided") -> None:
    """Shared warn logic for /warn command and 'Пред' text command."""
    lang = await get_user_lang(message)
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer(t("warn_no_reply", lang))
        return

    target = message.reply_to_message.from_user

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        admin = await get_or_create_user(session, telegram_id=message.from_user.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)

        await add_warning(session, chat.id, user.id, admin.id, reason)
        warn_count = await increment_warnings(session, chat.id, user.id)

        mention = get_user_mention(target)
        await message.answer(t("warn_message", lang, user=mention, count=warn_count, reason=reason))
        await log_action(session, message.chat.id, target.id, "warned", admin_id=message.from_user.id, details=reason)

        if warn_count >= 3:
            await mute_member(session, chat.id, user.id, 3600)
            await message.answer(t("warn_auto_muted", lang, user=mention))


async def _do_mute(message: Message, args: str = "") -> None:
    """Shared mute logic for /mute command and 'Мут' text command."""
    lang = await get_user_lang(message)
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer(t("mute_no_reply", lang))
        return

    target = message.reply_to_message.from_user
    duration = 3600
    reason = "No reason"
    if args:
        parts = args.split(maxsplit=1)
        duration = _parse_duration(parts[0])
        if len(parts) > 1:
            reason = parts[1]

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await mute_member(session, chat.id, user.id, duration)
        await log_action(session, message.chat.id, target.id, "muted", admin_id=message.from_user.id, details=f"{duration}s: {reason}")

    try:
        until_date = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
    except Exception as e:
        await message.answer(f"⚠️ Cannot restrict: {e}. Make bot admin!")

    await message.answer(t("mute_message", lang, user=get_user_mention(target), duration=_format_duration(duration), reason=reason))


async def _do_ban(message: Message, reason: str = "No reason") -> None:
    """Shared ban logic for /ban command and 'Бан' text command."""
    lang = await get_user_lang(message)
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Ответь на сообщение пользователя, чтобы забанить.")
        return

    target = message.reply_to_message.from_user

    try:
        await message.bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
        )
    except Exception as e:
        await message.answer(f"⚠️ Cannot ban: {e}. Make bot admin!")
        return

    mention = get_user_mention(target)
    await message.answer(f"🔨 <b>{mention}</b> забанен. Причина: {reason}")

    async with async_session_factory() as session:
        await log_action(
            session, message.chat.id, target.id, "banned",
            admin_id=message.from_user.id, details=reason,
        )


@router.message(Command("warn"), IsGroup(), HasRank(1))
async def cmd_warn(message: Message) -> None:
    reason = message.text.removeprefix("/warn").strip() or "No reason provided"
    await _do_warn(message, reason)


@router.message(Command("unwarn"), IsGroup(), HasRank(1))
async def cmd_unwarn(message: Message) -> None:
    lang = await get_user_lang(message)
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer(t("unwarn_no_reply", lang))
        return

    target = message.reply_to_message.from_user
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)

        warnings = await get_user_warnings(session, chat.id, user.id)
        if not warnings:
            await message.answer(t("unwarn_no_warnings", lang))
            return

        last = warnings[0]
        await session.delete(last)
        await session.commit()

        member = await get_chat_member(session, chat.id, user.id)
        if member and member.warnings_count > 0:
            member.warnings_count -= 1
            await session.commit()

        count = member.warnings_count if member else 0
        await message.answer(t("unwarn_message", lang, user=get_user_mention(target), count=count))


@router.message(Command("mute"), IsGroup(), HasRank(1))
async def cmd_mute(message: Message) -> None:
    args = message.text.removeprefix("/mute").strip()
    await _do_mute(message, args)


@router.message(Command("unmute"), IsGroup(), HasRank(1))
async def cmd_unmute(message: Message) -> None:
    lang = await get_user_lang(message)
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer(t("unmute_no_reply", lang))
        return

    target = message.reply_to_message.from_user
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        await unmute_member(session, chat.id, user.id)
        await log_action(session, message.chat.id, target.id, "unmuted", admin_id=message.from_user.id)

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True,
                can_change_info=True,
                can_pin_messages=True,
                can_manage_topics=True,
            ),
        )
    except Exception as e:
        await message.answer(f"⚠️ Cannot unrestrict: {e}")

    await message.answer(t("unmute_message", lang, user=get_user_mention(target)))


@router.message(Command("ban"), IsGroup(), HasRank(2))
async def cmd_ban(message: Message) -> None:
    reason = message.text.removeprefix("/ban").strip() or "No reason"
    await _do_ban(message, reason)


@router.message(Command("warnings"), IsGroup(), HasRank(1))
async def cmd_list_warnings(message: Message) -> None:
    lang = await get_user_lang(message)
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    if target is None:
        await message.answer("Reply to a user to see their warnings.")
        return

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        warnings = await get_user_warnings(session, chat.id, user.id)

    if not warnings:
        await message.answer(t("warnings_empty", lang, user=get_user_mention(target)))
        return

    lines = [t("warnings_title", lang, user=get_user_mention(target))]
    for i, w in enumerate(warnings, 1):
        lines.append(f"{i}. {w.reason or 'No reason'} ({w.created_at.strftime('%Y-%m-%d %H:%M')})")

    await message.answer("\n".join(lines))


# ── Text aliases: "Пред", "Мут", "Бан" (reply to message) ────────────────────

@router.message(F.text.in_({"Пред", "пред", "ПРЕД"}), F.reply_to_message, IsGroup(), HasRank(1))
async def text_warn(message: Message) -> None:
    """Reply with 'Пред' to warn a user."""
    await _do_warn(message, "Текстовая команда")


@router.message(F.text.in_({"Мут", "мут", "МУТ"}), F.reply_to_message, IsGroup(), HasRank(1))
async def text_mute(message: Message) -> None:
    """Reply with 'Мут' to mute a user."""
    await _do_mute(message)


@router.message(F.text.in_({"Бан", "бан", "БАН"}), F.reply_to_message, IsGroup(), HasRank(2))
async def text_ban(message: Message) -> None:
    """Reply with 'Бан' to ban a user."""
    await _do_ban(message, "Текстовая команда")
