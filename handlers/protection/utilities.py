"""Useful group utilities: pin, admins, mutelist, clean, allowlink."""

import asyncio
import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import add_note, get_or_create_chat, update_chat_settings
from db.queries import get_or_create_user
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "utilities"


# ── /pin ──────────────────────────────────────────────────────────────────────

@router.message(Command("pin"), IsGroup(), HasRank(2))
async def cmd_pin(message: Message) -> None:
    """Pin a message. Reply to a message with /pin"""
    if not message.reply_to_message:
        await message.answer("Reply to a message to pin it!")
        return
    try:
        await message.reply_to_message.pin(disable_notification=True)
        await message.answer("📌 Pinned!")
    except Exception as e:
        await message.answer(f"⚠️ Cannot pin: {e}")


@router.message(Command("unpin"), IsGroup(), HasRank(2))
async def cmd_unpin(message: Message) -> None:
    """Unpin a message. Reply to a message with /unpin or use /unpin all"""
    args = message.text.removeprefix("/unpin").strip()
    try:
        if args.lower() == "all":
            await message.chat.unpin_all_messages()
            await message.answer("📌 All unpinned!")
        elif message.reply_to_message:
            await message.reply_to_message.unpin()
            await message.answer("📌 Unpinned!")
        else:
            await message.answer("Reply to a message or use /unpin all")
    except Exception as e:
        await message.answer(f"⚠️ Cannot unpin: {e}")


# ── /admins ────────────────────────────────────────────────────────────────────

@router.message(Command("admins"), IsGroup())
async def cmd_admins(message: Message) -> None:
    """List all Telegram admins + bot-level admins."""
    lines = ["👑 <b>Admins:</b>"]

    # Telegram admins
    try:
        admins = await message.chat.get_administrators()
        for a in admins:
            user = a.user
            role = "👑 Creator" if a.status == "creator" else "🛡 Admin"
            name = f"@{user.username}" if user.username else f"<b>{user.first_name}</b>"
            lines.append(f"{role}: {name}")
    except Exception:
        lines.append("(cannot fetch Telegram admin list)")

    # Bot-level admins
    async with async_session_factory() as session:
        from db.queries import get_or_create_chat, list_chat_admins
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        bot_admins = await list_chat_admins(session, chat.id)

    if bot_admins:
        lines.append("")
        lines.append("🤖 <b>Bot admins:</b>")
        for a, rank in bot_admins:
            name = f"@{a.username}" if a.username else f"<b>{a.first_name or 'Unknown'}</b>"
            rank_icons = {1: "🔰", 2: "🛡️", 3: "👑"}
            icon = rank_icons.get(rank, "❓")
            lines.append(f"• {icon} {name}")

    await message.answer("\n".join(lines))


# ── /mutelist ──────────────────────────────────────────────────────────────────

@router.message(Command("mutelist"), IsGroup(), HasRank(1))
async def cmd_mutelist(message: Message) -> None:
    """List all muted users."""
    from db.models import ChatMember
    from sqlalchemy import select

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat.id,
            ChatMember.is_muted == True,
        )
        result = await session.execute(stmt)
        muted = list(result.scalars().all())

    if not muted:
        await message.answer("🔇 No one is muted.")
        return

    now = datetime.datetime.now()
    lines = ["🔇 <b>Muted users:</b>"]
    for m in muted:
        from db.queries import get_user_by_id
        async with async_session_factory() as s:
            user = await get_user_by_id(s, m.user_id)
        name = user.first_name if user else f"User #{m.user_id}"
        remaining = ""
        if m.muted_until and m.muted_until > now:
            remaining = f" ({int((m.muted_until - now).total_seconds()//60)}min left)"
        lines.append(f"• {name}{remaining}")
    await message.answer("\n".join(lines))


# ── /clean ─────────────────────────────────────────────────────────────────────

@router.message(Command("clean"), IsGroup(), HasRank(2))
async def cmd_clean(message: Message) -> None:
    """Delete all bot messages in the last N messages."""
    status = await message.answer("🧹 Cleaning...")
    deleted = 0
    try:
        async for msg in message.chat.history(limit=200):
            if msg.from_user and msg.from_user.id == message.bot.id:
                try:
                    await msg.delete()
                    deleted += 1
                except Exception:
                    pass
        await status.edit_text(f"🧹 Deleted {deleted} bot messages.")
    except Exception as e:
        await status.edit_text(f"⚠️ Error: {e}")


# ── /allowlink ─────────────────────────────────────────────────────────────────

@router.message(Command("allowlink"), IsGroup(), HasRank(2))
async def cmd_allowlink(message: Message) -> None:
    """Whitelist a domain. Usage: /allowlink <domain>"""
    domain = message.text.removeprefix("/allowlink").strip().lower()
    if not domain:
        await message.answer("Usage: /allowlink <domain>")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        settings = chat.settings or {}
        allowed = settings.get("allowed_domains", [])
        if domain not in allowed:
            allowed.append(domain)
            await update_chat_settings(session, chat.id, {"allowed_domains": allowed})
        await message.answer(f"✅ Domain <b>{domain}</b> whitelisted!")


# ── Auto-unmute (runs every 5 min via task) ───────────────────────────────────

async def auto_unmute_check(bot):
    """Background task: check and unmute expired mutes."""
    from db.models import Chat, ChatMember
    from sqlalchemy import select

    while True:
        await asyncio.sleep(300)  # 5 min
        try:
            async with async_session_factory() as session:
                from sqlalchemy import select
                now = datetime.datetime.now()
                stmt = select(ChatMember).join(Chat).where(
                    ChatMember.is_muted == True,
                    ChatMember.muted_until.isnot(None),
                    ChatMember.muted_until <= now,
                )
                result = await session.execute(stmt)
                expired = list(result.scalars().all())

                for m in expired:
                    m.is_muted = False
                    m.muted_until = None
                    # Try Telegram API unmute
                    try:
                        # We need bot here - will be passed via startup
                        pass
                    except Exception:
                        pass
                await session.commit()
        except Exception:
            pass
