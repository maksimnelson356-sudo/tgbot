from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_chat_member, get_or_create_chat, get_or_create_user, get_user_warnings
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "info"


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """Show chat/user ID. Usage: /id [reply]"""
    lang = await get_user_lang(message)

    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        lines = [
            f"👤 <b>{target.first_name}</b>",
            f"🆔 ID: <code>{target.id}</code>",
        ]
        if message.chat.type in ("group", "supergroup"):
            lines.append(f"💬 Chat ID: <code>{message.chat.id}</code>")
        await message.answer("\n".join(lines))
    else:
        lines = [
            f"🆔 Your ID: <code>{message.from_user.id}</code>",
        ]
        if message.chat.type in ("group", "supergroup"):
            lines.append(f"💬 Chat ID: <code>{message.chat.id}</code>")
        await message.answer("\n".join(lines))


@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    """Show detailed user info. Usage: /info [reply]"""
    lang = await get_user_lang(message)

    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user

    if target is None:
        return

    lines = [f"👤 <b>{target.first_name}</b>"]
    if target.last_name:
        lines.append(f"📛 Full name: {target.first_name} {target.last_name}")
    if target.username:
        lines.append(f"📧 Username: @{target.username}")
    lines.append(f"🆔 ID: <code>{target.id}</code>")
    if target.language_code:
        lines.append(f"🌐 Lang: {target.language_code}")

    # Get DB info (warnings, join date)
    if message.chat.type in ("group", "supergroup"):
        async with async_session_factory() as session:
            user = await get_or_create_user(
                session, telegram_id=target.id,
            )
            chat = await get_or_create_chat(
                session, telegram_id=message.chat.id,
            )

            member = await get_chat_member(session, chat.id, user.id)
            if member:
                if member.joined_at:
                    lines.append(f"📅 Joined: {member.joined_at.strftime('%Y-%m-%d')}")
                if member.warnings_count > 0:
                    lines.append(f"⚠️ Warnings: {member.warnings_count}")
                if member.is_muted:
                    lines.append("🔇 <b>MUTED</b>")

        # Check admin status
        try:
            chat_member = await message.chat.get_member(target.id)
            status_map = {
                "creator": "👑 Creator",
                "administrator": "🛡 Admin",
                "member": "👤 Member",
                "restricted": "🔒 Restricted",
                "left": "🚪 Left",
                "kicked": "🚫 Banned",
            }
            status = status_map.get(chat_member.status, chat_member.status)
            lines.append(f"📌 Role: {status}")
        except Exception:
            pass

    await message.answer("\n".join(lines))
