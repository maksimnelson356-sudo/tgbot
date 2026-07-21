"""Auto-reply to keywords. Admin sets up keyword → reply pairs."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, update_chat_settings
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "autoresponder"

SAVE_KEY = "autoreplies"  # stored in chat.settings JSON


@router.message(Command("addreply"), IsGroup(), HasRank(2))
async def cmd_addreply(message: Message) -> None:
    """Add auto-reply. Usage: /addreply keyword | response"""
    text = message.text.removeprefix("/addreply").strip()
    if "|" not in text:
        await message.answer('Usage: /addreply keyword | response')
        return
    kw, reply = text.split("|", 1)
    kw, reply = kw.strip().lower(), reply.strip()
    if not kw or not reply:
        await message.answer('Keyword and response required.')
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        replies = (chat.settings or {}).get(SAVE_KEY, {})
        replies[kw] = reply
        await update_chat_settings(session, chat.id, {SAVE_KEY: replies})

    await message.answer(f"✅ Auto-reply added: '{kw}' → '{reply}'")


@router.message(Command("delreply"), IsGroup(), HasRank(2))
async def cmd_delreply(message: Message) -> None:
    """Delete auto-reply. Usage: /delreply keyword"""
    kw = message.text.removeprefix("/delreply").strip().lower()
    if not kw:
        await message.answer("Usage: /delreply keyword")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        replies = (chat.settings or {}).get(SAVE_KEY, {})
        if kw in replies:
            del replies[kw]
            await update_chat_settings(session, chat.id, {SAVE_KEY: replies})
            await message.answer(f"✅ Deleted reply for '{kw}'")
        else:
            await message.answer(f"❌ No reply for '{kw}'")


@router.message(Command("listreplies"), IsGroup(), HasRank(2))
async def cmd_listreplies(message: Message) -> None:
    """List all auto-replies."""
    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        replies = (chat.settings or {}).get(SAVE_KEY, {})
    if not replies:
        await message.answer("No auto-replies set.")
        return
    lines = ["📝 <b>Auto-replies:</b>"]
    for kw, reply in replies.items():
        lines.append(f"• <b>{kw}</b> → {reply[:30]}...")
    await message.answer("\n".join(lines))


@router.message(IsGroup(), F.text, ~F.text.startswith("/"))
async def check_autoreply(message: Message) -> None:
    """Check incoming messages against auto-replies."""
    if message.from_user is None or message.text is None:
        return
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except Exception:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        replies = (chat.settings or {}).get(SAVE_KEY, {})
        if not replies:
            return

    text_lower = message.text.lower()
    for kw, reply in replies.items():
        if kw in text_lower:
            await message.answer(reply)
            break
