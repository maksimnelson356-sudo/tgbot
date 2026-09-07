"""AI moderation service using Google Gemini — checks media and text for Telegram ToS violations."""

import base64
import json
import logging
from typing import Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Per-chat cooldown to avoid rate limits: skip AI check if last call was <2s ago
_last_call_times: dict[int, float] = {}
_MIN_INTERVAL: float = 2.0
_MAX_TRACKED_CHATS = 1000


import time

_MAX_CALL_AGE: float = 300.0  # 5 minutes — entries older than this are always pruned


def _prune_last_calls(now: float) -> None:
    """Drop stale per-chat markers: time-bound cleanup + LRU eviction."""
    # Prune entries older than _MAX_CALL_AGE (time-bound cleanup)
    stale = [cid for cid, ts in _last_call_times.items() if now - ts >= _MAX_CALL_AGE]
    for cid in stale:
        _last_call_times.pop(cid, None)

    # LRU eviction: if still over capacity, drop oldest entries
    if len(_last_call_times) > _MAX_TRACKED_CHATS:
        sorted_entries = sorted(_last_call_times.items(), key=lambda x: x[1])
        for cid, _ in sorted_entries[:len(_last_call_times) - _MAX_TRACKED_CHATS]:
            _last_call_times.pop(cid, None)

_MODERATION_PROMPT = """You are a content moderation assistant for a Telegram group chat. Analyze the following content and determine if it violates Telegram's Terms of Service or the group's rules.

Telegram prohibits:
- Pornography, sexual content, nudity
- Violence, gore, graphic content
- Terrorism, extremism, hate speech
- Drug use, self-harm, suicide promotion
- Spam, scams, phishing
- Child exploitation
- Personal data exposure (doxxing)
- Harassment, bullying, threats

Return ONLY a JSON object with this exact format:
{
  "allowed": true/false,
  "category": "safe" or one of: "nsfw", "violence", "terrorism", "hate_speech", "drugs", "self_harm", "spam", "scam", "doxxing", "harassment", "other",
  "reason": "brief explanation in Russian"
}

Be strict but reasonable. Art, medical content, news reporting, and educational content about sensitive topics is generally allowed if not gratuitous."""


async def check_text(text: str, chat_id: int = 0) -> Optional[dict]:
    """Analyze text message for Telegram ToS violations using Gemini."""
    import time
    global _last_call_times

    if not settings.GOOGLE_API_KEY or not text.strip():
        return None

    # Rate limit protection: skip if called too recently (per-chat)
    now = time.time()
    if now - _last_call_times.get(chat_id, 0) < _MIN_INTERVAL:
        return None
    _prune_last_calls(now)
    _last_call_times[chat_id] = now

    payload = {
        "contents": [{"parts": [{"text": f"{_MODERATION_PROMPT}\n\nText to analyze:\n{text}"}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_GEMINI_URL}?key={settings.GOOGLE_API_KEY}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Gemini API error: %s", resp.status)
                    return None
                data = await resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                text_out = text_out.removeprefix("```json").removesuffix("```").strip()
                return json.loads(text_out)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.warning("Gemini text response parse error: %s", e)
        return None
    except Exception as e:
        logger.warning("Gemini text check failed: %s", e)
        return None


async def check_photo(photo_bytes: bytes, mime_type: str = "image/jpeg", chat_id: int = 0) -> Optional[dict]:
    """Analyze a photo for Telegram ToS violations using Gemini Vision."""
    import time
    global _last_call_times

    if not settings.GOOGLE_API_KEY or not photo_bytes:
        return None

    # Rate limit protection (per-chat)
    now = time.time()
    if now - _last_call_times.get(chat_id, 0) < _MIN_INTERVAL:
        return None
    _prune_last_calls(now)
    _last_call_times[chat_id] = now

    b64 = base64.b64encode(photo_bytes).decode()

    payload = {
        "contents": [{
            "parts": [
                {"text": _MODERATION_PROMPT},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_GEMINI_URL}?key={settings.GOOGLE_API_KEY}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Gemini API error: %s", resp.status)
                    return None
                data = await resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                text_out = text_out.removeprefix("```json").removesuffix("```").strip()
                return json.loads(text_out)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.warning("Gemini photo response parse error: %s", e)
        return None
    except Exception as e:
        logger.warning("Gemini photo check failed: %s", e)
        return None


async def check_photo_from_telegram(bot, file_id: str, chat_id: int = 0) -> Optional[dict]:
    """Download photo from Telegram and analyze it with Gemini."""
    try:
        file = await bot.get_file(file_id)
        photo_bytes = await bot.download_file(file.file_path)
        return await check_photo(photo_bytes.read(), chat_id=chat_id)
    except Exception as e:
        logger.warning("Failed to download/check photo: %s", e)
        return None
