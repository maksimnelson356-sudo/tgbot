import asyncio
import datetime
import html
import logging
import sys
from typing import Any, Coroutine, Optional

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message, User as AiogramUser

logger = logging.getLogger(__name__)

# Strong references to fire-and-forget tasks.
# Without this, the event loop holds only weak refs and suspended
# tasks may be garbage-collected mid-flight (Python docs warning).
_background_tasks: set[asyncio.Task] = set()

# Scheduled auto-deletions: (chat_id, message_id) -> task.
# Lets /clean cancel pending deletions and remove messages immediately.
_pending_deletes: dict[tuple[int, int], asyncio.Task] = {}


def pop_pending_delete(chat_id: int, message_id: int) -> Optional[asyncio.Task]:
    """Unregister and return a scheduled deletion task, if any."""
    return _pending_deletes.pop((chat_id, message_id), None)


def pending_message_ids(chat_id: int) -> list[int]:
    """IDs of messages awaiting scheduled deletion in the given chat."""
    return [mid for (cid, mid) in list(_pending_deletes) if cid == chat_id]


def spawn(coro: Coroutine[Any, Any, Any], name: Optional[str] = None) -> asyncio.Task:
    """Create a tracked background task that survives GC and logs crashes."""
    task = asyncio.get_running_loop().create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def _log_task_exception(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.error(
            "Background task %s crashed", task.get_name(),
            exc_info=task.exception(),
        )


def schedule_delete(message: Message, delay: float = 5.0) -> None:
    """Schedule a message for deletion after a delay (non-blocking, tracked)."""
    key = (message.chat.id, message.message_id)
    old = _pending_deletes.get(key)
    if old is not None and not old.done():
        old.cancel()
    task = spawn(delete_after(message, delay), name=f"delete_{message.chat.id}_{message.message_id}")
    _pending_deletes[key] = task


async def delete_after(message: Message, delay: float = 5.0) -> None:
    """Delete a message after a delay (in seconds)."""
    await asyncio.sleep(delay)
    _pending_deletes.pop((message.chat.id, message.message_id), None)
    try:
        await message.delete()
    except Exception:
        pass


def get_user_mention(user: AiogramUser) -> str:
    """Get a formatted HTML-safe clickable mention for a user."""
    return f'<a href="tg://user?id={user.id}">{html.escape(user.first_name or "User")}</a>'


def display_name(obj: Any, default: str = "User") -> str:
    """HTML-safe display name for an aiogram User or a DB user row."""
    username = getattr(obj, "username", None)
    if username:
        return f"@{escape_html(username)}"
    name = (getattr(obj, "first_name", None) or "").strip()
    return escape_html(name) if name else default


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
        return f"{hours}h {minutes}m" if minutes else f"{hours}m"
    if seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    return f"{seconds}s"


def escape_html(text: Any) -> str:
    """Escape HTML special characters (safe on non-str input)."""
    return html.escape(str(text or ""), quote=False)


def keep_next(message: Message, delay: float = 600.0) -> None:
    """Make the NEXT ``message.answer()``/``reply()`` persist longer.

    Must be called BEFORE answering. The bot's auto-delete monkey-patch
    will keep that reply for ``delay`` seconds instead of 15.
    Use for reference content: leaderboards, rules, profiles, lists.
    """
    try:
        message._autodel_delay = delay
    except Exception:
        pass


async def shutdown_background_tasks(timeout: float = 5.0) -> None:
    """Cancel all tracked background tasks gracefully."""
    for task in list(_background_tasks):
        task.cancel()
    if _background_tasks:
        await asyncio.wait(list(_background_tasks), timeout=timeout)
