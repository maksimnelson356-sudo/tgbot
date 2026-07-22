"""Background scheduler — sends due posts automatically."""

import asyncio
import logging

from db.base import async_session_factory
from db.queries import get_due_posts, update_post_last_sent

logger = logging.getLogger(__name__)

_scheduler_task = None


async def _scheduler_loop(bot) -> None:
    """Check for due posts every 60 seconds."""
    logger.info("Scheduler loop started")
    while True:
        try:
            async with async_session_factory() as session:
                due_posts = await get_due_posts(session)
                for post in due_posts:
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
                        logger.info("Scheduled post %s sent to chat %s", post.id, post.chat_telegram_id)
                    except Exception as e:
                        logger.warning("Failed to send scheduled post %s: %s", post.id, e)
                        await update_post_last_sent(session, post.id)
        except Exception as e:
            logger.warning("Scheduler loop error: %s", e)

        await asyncio.sleep(60)


def start_scheduler(bot) -> None:
    """Start the background scheduler task."""
    global _scheduler_task
    loop = asyncio.get_event_loop()
    _scheduler_task = loop.create_task(_scheduler_loop(bot))
    logger.info("Scheduler task created")


def stop_scheduler() -> None:
    """Stop the background scheduler task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Scheduler task cancelled")
