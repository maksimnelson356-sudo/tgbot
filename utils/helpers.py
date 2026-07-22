import asyncio
import datetime
from typing import Optional

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message, User as AiogramUser


async def delete_after(message: Message, delay: float = 5.0) -> None:
    """Delete a message after a delay (in seconds)."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def schedule_delete(message: Message, delay: float = 5.0) -> None:
    """Schedule a message for deletion after a delay (non-blocking)."""
    asyncio.create_task(delete_after(message, delay))


def get_user_mention(user: AiogramUser) -> str:
    """Get a formatted mention for a user."""
    if user.username:
        return f"@{user.username}"
    return f"<b>{user.first_name}</b>"


def format_time(dt: Optional[datetime.datetime]) -> str:
    """Format datetime to human-readable string."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M")


def seconds_to_str(seconds: int) -> str:
    """Convert seconds to human-readable string."""
    if seconds >= 86400:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    if seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    return f"{seconds}s"


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
