"""Reminder handler — /remind 2h buy milk."""
import re
from datetime import timedelta, datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import create_reminder

router = Router()
router.name = "remind"

_DURATION_RE = re.compile(r"(\d+)\s*(m|min|h|hour|d|day|s|sec)?", re.IGNORECASE)


def _parse_duration(text: str) -> int:
    """Parse duration string to seconds."""
    match = _DURATION_RE.match(text)
    if not match:
        return 0
    amount = int(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in ("s", "sec"):
        return amount
    if unit in ("m", "min"):
        return amount * 60
    if unit in ("h", "hour"):
        return amount * 3600
    if unit in ("d", "day"):
        return amount * 86400
    return amount * 60  # default minutes


@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    """Set a reminder. Usage: /remind 2h buy milk"""
    text = message.text.removeprefix("/remind").strip()
    if not text:
        await message.answer(
            "⏰ Usage: /remind <time> <message>\n"
            "Examples:\n"
            "  /remind 30m call mom\n"
            "  /remind 2h buy groceries\n"
            "  /remind 1d check email"
        )
        return

    parts = text.split(maxsplit=1)
    duration = _parse_duration(parts[0])
    if duration <= 0 or duration > 86400 * 30:  # max 30 days
        await message.answer("⏰ Invalid duration. Use: 30m, 2h, 1d (max 30 days)")
        return

    reminder_text = parts[1] if len(parts) > 1 else "⏰ Reminder!"
    remind_at = datetime.now() + timedelta(seconds=duration)

    async with async_session_factory() as session:
        await create_reminder(
            session,
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            text=reminder_text,
            remind_at=remind_at,
        )

    hours = duration // 3600
    mins = (duration % 3600) // 60
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m"
    await message.answer(f"⏰ Reminder set for {time_str} from now!")
