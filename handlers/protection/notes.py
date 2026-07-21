from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import add_note, delete_note, get_or_create_chat, get_or_create_user, get_user_notes
from filters.admin import HasRank
from filters.chat_type import IsGroup

router = Router()
router.name = "notes"


@router.message(Command("note"), IsGroup(), HasRank(2))
async def cmd_note(message: Message) -> None:
    """Add a note about a user. Usage: /note <reply> text"""
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Reply to a user to add a note about them.")
        return

    text = message.text.removeprefix("/note").strip()
    if not text:
        await message.answer("Usage: /note <reply> <text>")
        return

    target = message.reply_to_message.from_user

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        admin = await get_or_create_user(session, telegram_id=message.from_user.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)

        note = await add_note(session, chat.id, user.id, admin.id, text)
        mention = f"@{target.username}" if target.username else f"<b>{target.first_name}</b>"

        await message.answer(f"📝 Note added for {mention} (ID: {note.id})")


@router.message(Command("notes"), IsGroup(), HasRank(2))
async def cmd_notes(message: Message) -> None:
    """List notes about a user. Usage: /notes <reply>"""
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user

    if target is None:
        await message.answer("Reply to a user to see their notes.")
        return

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        notes = await get_user_notes(session, chat.id, user.id)

    mention = f"@{target.username}" if target.username else f"<b>{target.first_name}</b>"

    if not notes:
        await message.answer(f"No notes for {mention}.")
        return

    lines = [f"📝 <b>Notes for {mention}</b>"]
    for i, n in enumerate(notes, 1):
        # Get admin name
        admin_name = f"admin#{n.admin_id}"
        lines.append(f"{i}. [{n.id}] {n.text} ({n.created_at.strftime('%Y-%m-%d')})")

    await message.answer("\n".join(lines))


@router.message(Command("delnote"), IsGroup(), HasRank(2))
async def cmd_delnote(message: Message) -> None:
    """Delete a note by ID. Usage: /delnote <note_id>"""
    args = message.text.removeprefix("/delnote").strip()
    if not args:
        await message.answer("Usage: /delnote <note_id>")
        return

    try:
        note_id = int(args)
    except ValueError:
        await message.answer("Invalid note ID. Usage: /delnote <note_id>")
        return

    async with async_session_factory() as session:
        success = await delete_note(session, note_id)
        if success:
            await message.answer(f"✅ Note {note_id} deleted.")
        else:
            await message.answer(f"❌ Note {note_id} not found.")
