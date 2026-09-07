import json
import logging
import re

import aiohttp
from aiogram import Router, F
from aiogram import exceptions as aiogram_exceptions
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    get_or_create_chat,
    get_or_create_user,
    log_action,
)
from handlers.protection.moderation_helpers import handle_warning, handle_media_moderation
from filters.chat_type import IsGroup
from services.content_filter import has_email, has_phone
from services.spam_detector import spam_detector
from utils.helpers import display_name, escape_html
from utils.i18n import t
from utils.lang_helper import get_user_lang

logger = logging.getLogger(__name__)

router = Router()
router.name = "moderation"

# Homoglyph map: Latin lookalikes → Cyrillic
_HOMOGLYPH_MAP: dict[str, str] = {
    "a": "а",  # Latin a → Cyrillic а
    "e": "е",  # Latin e → Cyrillic е
    "o": "о",  # Latin o → Cyrillic о
    "p": "р",  # Latin p → Cyrillic р
    "c": "с",  # Latin c → Cyrillic с
    "y": "у",  # Latin y → Cyrillic у
    "x": "х",  # Latin x → Cyrillic х
    "k": "к",  # Latin k → Cyrillic к
    "m": "м",  # Latin m → Cyrillic м
    "t": "т",  # Latin t → Cyrillic т
    "b": "в",  # Latin b → Cyrillic в
    "h": "н",  # Latin h → Cyrillic н (visual match in some fonts)
    "i": "і",  # Latin i → Cyrillic і
    "u": "и",  # Latin u → Cyrillic и (lowercase visual match)
}

# Also build reverse: Cyrillic → Latin (for English bad words)
_REVERSE_HOMOGLYPH: dict[str, str] = {v: k for k, v in _HOMOGLYPH_MAP.items()}


def normalize_text(text: str) -> str:
    """Normalize homoglyph characters to catch bypass attempts.

    Converts Latin lookalikes to Cyrillic (for Russian bad words)
    and Cyrillic lookalikes to Latin (for English bad words).
    Returns normalized lowercase text.
    """
    result = []
    for char in text.lower():
        # Latin → Cyrillic
        if char in _HOMOGLYPH_MAP:
            result.append(_HOMOGLYPH_MAP[char])
        # Cyrillic → Latin
        elif char in _REVERSE_HOMOGLYPH:
            result.append(_REVERSE_HOMOGLYPH[char])
        else:
            result.append(char)
    return "".join(result)


_DEFAULT_BAD_WORDS: list[str] = [
    "мат", "хуй", "пизд", "ебал", "еблан", "бляд", "гандон",
    "шлюх", "залуп", "мудак", "пидор", "петух", "гомик",
    "fuck", "shit", "asshole", "bitch", "bastard",
]

_NSFW_WORDS: list[str] = [
    # Russian NSFW
    "порно", "порн", "секс", "xxx", "18+",
    "эротика", "инцест", "жопа", "сосать", "член",
    "вагин", "пенис", "ораль", "аналь", "минет",
    "гей", "лесби", "зоофил", "некрофил",
    "порнух", "голая", "голый", "обнаж",
    "сноша", "траха", "шлюха",
    # English NSFW
    "porn", "sex", "nsfw", "xxx",
    "erotic", "fucking", "dick", "cock",
    "pussy", "tits", "boobs", "naked",
    "nude", "hentai", "rule34",
    "milf", "onlyfans",
]

_URL_RE = re.compile(r"https?://\S+|t\.me/\S+", re.IGNORECASE)

# Common NSFW media domains
_NSFW_DOMAINS = [
    "pornhub", "xvideos", "xnxx", "xhamster", "redtube",
    "onlyfans", "stripchat", "chaturbate", "youporn",
]


def _extract_domains(text: str) -> set[str]:
    """Extract lowercase hostnames from any URLs inside the text."""
    from urllib.parse import urlparse

    domains: set[str] = set()
    for url in _URL_RE.findall(text):
        url = url.rstrip(".,;!?)")  # strip trailing punctuation
        if "://" not in url:
            url = f"https://{url}"
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            continue
        if host:
            domains.add(host.lower())
    return domains


def _domain_is_allowed(host: str, allowed_domains: list) -> bool:
    """Match a hostname against the admin-configured whitelist.

    Exact matches and subdomains pass: allowing ``example.com`` also
    lets ``sub.example.com`` through.
    """
    allowed = {d.lower().lstrip(".") for d in (allowed_domains or []) if d}
    return any(host == d or host.endswith("." + d) for d in allowed)


@router.message(IsGroup(), F.text, ~F.text.startswith("/"))
async def moderate_message(message: Message) -> None:
    """Check messages for spam, bad words, links, and NSFW content."""
    if message.from_user is None or message.text is None:
        return

    lang = await get_user_lang(message)

    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except aiogram_exceptions.TelegramForbiddenError:
        return
    except aiogram_exceptions.TelegramBadRequest:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(
            session, telegram_id=message.chat.id,
        )
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id,
        )

        settings = chat.settings or {}
        text = message.text
        reason = None

        if not settings.get("moderation_enabled", True):
            return

        # Spam check
        spam_result = spam_detector.check(text, message.from_user.id)
        if spam_result.is_spam:
            reason = t("mod_spam", lang, reason=spam_result.reason or "")

        # Bad words (with homoglyph normalization)
        if reason is None and settings.get("bad_words_enabled", True):
            bad_words = settings.get("bad_words") or _DEFAULT_BAD_WORDS
            text_normalized = normalize_text(text)
            for word in bad_words:
                if word.lower() in text or word.lower() in text_normalized:
                    reason = t("mod_profanity", lang, word=word)
                    break

        # NSFW text filter (with homoglyph normalization)
        if reason is None and settings.get("nsfw_filter_enabled", True):
            text_lower = text.lower()
            text_normalized = normalize_text(text)
            for word in _NSFW_WORDS:
                if word.lower() in text_lower or word.lower() in text_normalized:
                    reason = "NSFW: " + word
                    break

        # NSFW link check
        if reason is None and settings.get("nsfw_filter_enabled", True):
            text_lower = text.lower()
            for domain in _NSFW_DOMAINS:
                if domain in text_lower:
                    reason = "NSFW link"
                    break

        # Links
        if reason is None and settings.get("filter_links", False):
            domains = _extract_domains(text)
            if domains and not all(_domain_is_allowed(d, settings.get("allowed_domains", [])) for d in domains):
                reason = t("mod_links", lang)

        # (Media filtering lives in moderate_filtered_media — text never has media.)

        # Anti-forward (block forwarded channel messages)
        if reason is None and settings.get("antiforward_enabled", False):
            if message.forward_from_chat:
                reason = "Forwarded message blocked"

        # Anti-phone/email
        if reason is None and settings.get("antispam_contacts", False):
            if has_phone(text) or has_email(text):
                reason = "Phone/email blocked"

        # AI moderation (Gemini) — fallback if word-lists missed something
        if reason is None and settings.get("moderation_enabled", True):
            from config import settings as bot_settings
            if bot_settings.GOOGLE_API_KEY:
                try:
                    from services.ai_moderation import check_text
                    ai_result = await check_text(text, chat_id=message.chat.id)
                    if ai_result and not ai_result.get("allowed", True):
                        reason = escape_html(
                            f"AI: {ai_result.get('category', 'violation')} — {ai_result.get('reason', '')}"
                        )
                except (KeyError, IndexError, json.JSONDecodeError):
                    pass
                except aiohttp.ClientError:
                    pass
                except Exception as e:
                    logger.warning("AI moderation check failed: %s", e)

        if reason is not None:
            try:
                await message.delete()
            except aiogram_exceptions.TelegramBadRequest:
                pass

            await handle_warning(
                session, chat, user, message, reason, lang, settings
            )


# Media-block handler — makes the admin-panel `filter_media` toggle work:
# when enabled, ALL media from non-admins is deleted.
@router.message(IsGroup(), F.photo | F.video | F.animation | F.document, ~F.text.startswith("/"))
async def moderate_filtered_media(message: Message) -> None:
    """Delete all media if the chat has `filter_media` enabled."""
    if message.from_user is None:
        return
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except (aiogram_exceptions.TelegramForbiddenError, aiogram_exceptions.TelegramBadRequest):
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        settings = chat.settings or {}
        if not settings.get("filter_media", False):
            return

        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        lang = await get_user_lang(message)

        if not settings.get("moderation_enabled", True):
            return
        await handle_media_moderation(
            session, chat, user, message, t("mod_media", lang), lang, settings
        )


@router.message(IsGroup(), F.photo | F.video | F.animation, ~F.text.startswith("/"))
async def moderate_nsfw_media(message: Message) -> None:
    """Check media messages for NSFW/ToS-violating content using AI."""
    if message.from_user is None:
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except (aiogram_exceptions.TelegramForbiddenError, aiogram_exceptions.TelegramBadRequest):
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(
            session, telegram_id=message.chat.id,
        )
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id,
        )

        settings = chat.settings or {}
        if not settings.get("moderation_enabled", True) or not settings.get("nsfw_filter_enabled", True):
            return

        lang = await get_user_lang(message)
        text = (message.caption or "").lower()

        # Check caption for NSFW words (with homoglyph normalization)
        if text:
            text_normalized = normalize_text(text)
            for word in _NSFW_WORDS:
                if word.lower() in text or word.lower() in text_normalized:
                    await handle_media_moderation(
                        session, chat, user, message, f"NSFW: {word}", lang, settings
                    )
                    return

            # Check caption for NSFW domains
            for domain in _NSFW_DOMAINS:
                if domain in text:
                    await handle_media_moderation(
                        session, chat, user, message, f"NSFW link: {domain}", lang, settings
                    )
                    return

        # AI image analysis (Gemini Vision)
        from config import settings as bot_settings
        if bot_settings.GOOGLE_API_KEY and message.photo:
            try:
                from services.ai_moderation import check_photo_from_telegram
                ai_result = await check_photo_from_telegram(message.bot, message.photo[-1].file_id, chat_id=message.chat.id)
                if ai_result and not ai_result.get("allowed", True):
                    reason = escape_html(
                        f"AI: {ai_result.get('category', 'violation')} — {ai_result.get('reason', '')}"
                    )
                    await handle_media_moderation(
                        session, chat, user, message, reason, lang, settings
                    )
                    return
            except (KeyError, IndexError, json.JSONDecodeError, aiohttp.ClientError) as e:
                logger.warning("AI photo moderation failed: %s", e)


# Anti-forward handler (catches ALL forwarded messages)
@router.message(IsGroup(), F.forward_from_chat | F.forward_from | F.forward_sender_name)
async def moderate_forwarded(message: Message) -> None:
    """Block forwarded messages if antiforward is enabled."""
    if message.from_user is None:
        return
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except (aiogram_exceptions.TelegramForbiddenError, aiogram_exceptions.TelegramBadRequest):
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        if not (chat.settings or {}).get("antiforward_enabled", False):
            return

        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        lang = await get_user_lang(message)

        try:
            await message.delete()
        except (aiogram_exceptions.TelegramBadRequest, aiogram_exceptions.TelegramForbiddenError):
            pass

        await handle_warning(
            session, chat, user, message, "Forwarded message blocked", lang, chat.settings or {}
        )


# NSFW-suggestive emoji often used in inappropriate stickers
_NSFW_EMOJI = {
    "🍆", "🍑", "💦", "👅", "🍌", "🌭", "🔥",
    "😈", "💋", "🫦", "🍓", "🥵", "🫣",
}


# NSFW keywords in sticker set names
_NSFW_STICKER_SET_KEYWORDS = [
    "porn", "hentai", "nsfw", "rule34", "18+", "sex",
    "boobs", "tits", "naked", "nude", "erotic",
    "порно", "хентай", "эротика", "голый", "голая",
    "18плюс", "18 плюс", "для взрослых",
]


@router.message(IsGroup(), F.sticker)
async def moderate_nsfw_sticker(message: Message) -> None:
    """Check stickers for NSFW content based on emoji and set name."""
    if message.from_user is None or message.sticker is None:
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except (aiogram_exceptions.TelegramForbiddenError, aiogram_exceptions.TelegramBadRequest):
        return

    lang = await get_user_lang(message)
    sticker_uid = message.sticker.file_unique_id

    async with async_session_factory() as session:
        chat = await get_or_create_chat(
            session, telegram_id=message.chat.id,
        )
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id,
        )

        settings = chat.settings or {}
        if not settings.get("moderation_enabled", True) or not settings.get("nsfw_filter_enabled", True):
            return

        # Check 0: Banned sticker list
        from db.queries import is_sticker_banned
        if await is_sticker_banned(session, chat.id, sticker_uid):
            is_nsfw = True
            sticker_emoji = (message.sticker.emoji or "") + " [banned]"
        else:
            # Check 1: Emoji
            sticker_emoji = (message.sticker.emoji or "")
            is_nsfw = sticker_emoji in _NSFW_EMOJI

        # Check 2: Sticker set name (if available)
        if not is_nsfw and message.sticker.set_name:
            set_name_lower = message.sticker.set_name.lower().replace("_", " ").replace("-", " ")
            for keyword in _NSFW_STICKER_SET_KEYWORDS:
                if keyword.lower() in set_name_lower:
                    is_nsfw = True
                    sticker_emoji = f"{sticker_emoji} ({message.sticker.set_name})"
                    break

        if is_nsfw:
            await handle_media_moderation(
                session, chat, user, message, f"NSFW sticker: {escape_html(sticker_emoji)}", lang, settings
            )
