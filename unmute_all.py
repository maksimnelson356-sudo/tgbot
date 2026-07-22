"""One-time script to unmute all restricted members in all groups."""
import asyncio
import os
import sqlite3

from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import ChatPermissions
from aiogram.client.session.aiohttp import AiohttpSession

load_dotenv()

FULL_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
    can_change_info=True,
    can_pin_messages=True,
    can_manage_topics=True,
)


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    session = AiohttpSession()
    bot.session = session

    conn = sqlite3.connect("data/tgbot.db")
    rows = conn.execute("""
        SELECT c.telegram_id, u.telegram_id
        FROM chat_members cm
        JOIN chats c ON cm.chat_id = c.id
        JOIN users u ON cm.user_id = u.id
    """).fetchall()
    conn.close()

    print(f"Found {len(rows)} member entries")

    unmuted = 0
    failed = 0
    for chat_tid, user_tid in rows:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_tid,
                user_id=user_tid,
                permissions=FULL_PERMS,
            )
            unmuted += 1
        except Exception as e:
            if "not enough rights" in str(e).lower() or "can't demote" in str(e).lower():
                pass
            else:
                failed += 1
                print(f"Failed chat={chat_tid} user={user_tid}: {e}")

    print(f"Done: unmuted {unmuted}, failed {failed}")
    await session.close()


asyncio.run(main())
