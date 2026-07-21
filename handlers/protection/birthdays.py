"""Birthday tracking for chat members."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, get_or_create_user, update_chat_settings
from filters.chat_type import IsGroup

router = Router()
router.name = "birthdays"

SAVE_KEY = "birthdays"


@router.message(Command("setbday"), IsGroup())
async def cmd_setbday(message: Message) -> None:
    """Set your birthday. Usage: /setbday DD.MM"""
    args = message.text.removeprefix("/setbday").strip()
    if not args or "." not in args:
        await message.answer("Usage: /setbday DD.MM (e.g. /setbday 15.03)")
        return
    parts = args.split(".")
    if len(parts) != 2:
        await message.answer("Usage: /setbday DD.MM")
        return
    day, month = parts
    if not day.isdigit() or not month.isdigit():
        await message.answer("Invalid date.")
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        bdays = (chat.settings or {}).get(SAVE_KEY, {})
        bdays[str(message.from_user.id)] = f"{int(day):02d}.{int(month):02d}"
        await update_chat_settings(session, chat.id, {SAVE_KEY: bdays})

    await message.answer(f"✅ Birthday set to {int(day):02d}.{int(month):02d}")


@router.message(Command("birthdays"), IsGroup())
async def cmd_birthdays(message: Message) -> None:
    """Show all birthdays this month."""
    import datetime
    now = datetime.datetime.now()

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        bdays = (chat.settings or {}).get(SAVE_KEY, {})
        if not bdays:
            await message.answer("No birthdays set. Use /setbday DD.MM")
            return

    lines = [f"🎂 <b>Birthdays this month ({now.month:02d}):</b>"]
    for uid_str, date_str in bdays.items():
        day, month = date_str.split(".")
        if int(month) == now.month:
            from db.queries import get_or_create_user
            async with async_session_factory() as s:
                user = await get_or_create_user(s, telegram_id=int(uid_str))
            name = user.first_name or f"User {uid_str}"
            lines.append(f"  • {name} — {int(day)} числа 🎉")

    if len(lines) == 1:
        lines.append("  No birthdays this month.")

    await message.answer("\n".join(lines))
