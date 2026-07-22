"""AI chat — bot responds to messages using Gemini when ai_chat_enabled."""

import logging

from aiogram import Router, F
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat
from filters.chat_type import IsGroup

router = Router()
router.name = "ai_chat"

logger = logging.getLogger(__name__)


@router.message(IsGroup(), F.text, ~F.text.startswith("/"), F.reply_to_message)
async def ai_chat_reply(message: Message) -> None:
    """Respond when someone replies to the bot's message and AI chat is enabled."""
    if message.from_user is None or message.text is None:
        return

    if message.reply_to_message is None:
        return
    if message.reply_to_message.from_user is None:
        return
    if message.reply_to_message.from_user.id != message.bot.id:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        chat_settings = chat.settings or {}
        if not chat_settings.get("ai_chat_enabled", False):
            return

    from config import settings as bot_settings
    if not bot_settings.GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set, skipping AI chat")
        return

    logger.info("AI chat: user=%s chat=%s text=%s", message.from_user.id, message.chat.id, message.text[:50])

    try:
        from services.ai_moderation import _GEMINI_URL
        import aiohttp, json

        payload = {
            "contents": [{"parts": [
                {"text": f"Ты умный и дружелюбный помощник в Telegram-группе. Отвечай кратко и по делу на русском языке. Не используй Markdown, просто plain text.\n\nСообщение от @{message.from_user.username or message.from_user.first_name}: {message.text}"}
            ]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_GEMINI_URL}?key={bot_settings.GOOGLE_API_KEY}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Gemini API error %d: %s", resp.status, body[:200])
                    return
                data = await resp.json()
                reply_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                await message.answer(reply_text)
                logger.info("AI chat reply sent to user=%s", message.from_user.id)
    except Exception as e:
        logger.warning("AI chat error: %s", e)
