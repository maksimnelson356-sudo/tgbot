"""Background scheduler — sends due posts and reminders automatically."""

import asyncio
import datetime
import logging
from typing import Optional

from db.base import async_session_factory
from db.queries import (
    deactivate_scheduled_post,
    get_due_posts,
    get_due_reminders,
    mark_reminder_sent,
    update_post_last_sent,
)
from utils.helpers import escape_html, spawn
from utils.time_utils import today_local

logger = logging.getLogger(__name__)

_scheduler_task = None

# Consecutive-failure counters for scheduled posts (in-memory backoff)
_post_failures: dict[int, int] = {}
_MAX_POST_FAILURES = 5

_message_log_retention_days = 30
_last_retention_date: Optional[datetime.date] = None


async def _run_message_log_retention() -> None:
    """Once a day, purge message_log rows older than the retention window."""
    global _last_retention_date
    today = today_local()
    if _last_retention_date == today:
        return
    try:
        from db.queries import delete_old_message_logs
        async with async_session_factory() as session:
            deleted = await delete_old_message_logs(session, _message_log_retention_days)
        if deleted:
            logger.info("MessageLog retention: deleted %d rows older than %dd",
                        deleted, _message_log_retention_days)
        _last_retention_date = today
    except Exception as e:
        logger.warning("MessageLog retention failed: %s", e)


async def _scheduler_loop(bot) -> None:
    """Check for due posts every 60 seconds."""
    global _post_failures
    logger.info("Scheduler loop started")
    while True:
        try:
            async with async_session_factory() as session:
                due_posts = await get_due_posts(session)
                for post in due_posts:
                    if _post_failures.get(post.id, 0) >= _MAX_POST_FAILURES:
                        continue
                    try:
                        if post.photo_file_id:
                            media_type = getattr(post, "media_type", None) or "photo"
                            if media_type == "video":
                                await bot.send_video(
                                    chat_id=post.chat_telegram_id,
                                    video=post.photo_file_id,
                                    caption=post.text,
                                )
                            elif media_type == "animation":
                                await bot.send_animation(
                                    chat_id=post.chat_telegram_id,
                                    animation=post.photo_file_id,
                                    caption=post.text,
                                )
                            elif media_type == "voice":
                                await bot.send_voice(
                                    chat_id=post.chat_telegram_id,
                                    voice=post.photo_file_id,
                                    caption=post.text,
                                )
                            elif media_type == "audio":
                                await bot.send_audio(
                                    chat_id=post.chat_telegram_id,
                                    audio=post.photo_file_id,
                                    caption=post.text,
                                )
                            elif media_type == "video_note":
                                await bot.send_video_note(
                                    chat_id=post.chat_telegram_id,
                                    video_note=post.photo_file_id,
                                )
                            elif media_type == "document":
                                await bot.send_document(
                                    chat_id=post.chat_telegram_id,
                                    document=post.photo_file_id,
                                    caption=post.text,
                                )
                            else:
                                await bot.send_photo(
                                    chat_id=post.chat_telegram_id,
                                    photo=post.photo_file_id,
                                    caption=post.text,
                                )
                        else:
                            await bot.send_message(
                                chat_id=post.chat_telegram_id,
                                text=post.text,
                            )
                        await update_post_last_sent(session, post.id)
                        _post_failures.pop(post.id, None)
                        logger.info("Scheduled post %s sent to chat %s", post.id, post.chat_telegram_id)
                    except Exception as e:
                        failures = _post_failures.get(post.id, 0) + 1
                        _post_failures[post.id] = failures
                        logger.warning("Failed to send scheduled post %s (%d/%d): %s",
                                       post.id, failures, _MAX_POST_FAILURES, e)
                        if failures >= _MAX_POST_FAILURES:
                            async with async_session_factory() as s2:
                                await deactivate_scheduled_post(s2, post.id)
                            _post_failures.pop(post.id, None)
                            logger.error("Scheduled post %s deactivated after %d failures",
                                         post.id, failures)
        except Exception as e:
            logger.warning("Scheduler loop error: %s", e)

        # Check reminders
        try:
            async with async_session_factory() as session:
                due_reminders = await get_due_reminders(session)
                for r in due_reminders:
                    try:
                        await bot.send_message(
                            chat_id=r.chat_id,
                            text=f"⏰ <b>Reminder:</b> {escape_html(r.text)}",
                        )
                        await mark_reminder_sent(session, r.id)
                        logger.info("Reminder %s sent to chat %s", r.id, r.chat_id)
                    except Exception as e:
                        logger.warning("Failed to send reminder %s: %s", r.id, e)
        except Exception as e:
            logger.warning("Reminder loop error: %s", e)

        # Daily housekeeping
        await _run_message_log_retention()

        # Engagement hooks (self-throttled: run at most once per day)
        try:
            from services.engagement import check_birthdays, weekly_digest
            await check_birthdays(bot)
            await weekly_digest(bot)
        except Exception as e:
            logger.warning("Engagement hooks failed: %s", e)

        await asyncio.sleep(60)


def start_scheduler(bot) -> None:
    """Start the background scheduler task (tracked — survives GC)."""
    global _scheduler_task
    _scheduler_task = spawn(_scheduler_loop(bot), name="scheduler_loop")
    logger.info("Scheduler task created")


def stop_scheduler() -> None:
    """Stop the background scheduler task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Scheduler task cancelled")
