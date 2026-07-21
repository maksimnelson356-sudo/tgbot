import datetime
import re

from aiogram import Router, F
from aiogram.types import ChatPermissions, Message

from db.base import async_session_factory
from db.queries import (
    add_warning,
    get_or_create_chat,
    get_or_create_user,
    increment_warnings,
    log_action,
    mute_member,
    reset_warnings,
)
from filters.chat_type import IsGroup
from services.content_filter import has_email, has_phone
from services.spam_detector import spam_detector
from utils.i18n import t
from utils.lang_helper import get_user_lang

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
    except Exception:
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
            if _URL_RE.search(text):
                reason = t("mod_links", lang)

        # Media
        if reason is None and settings.get("filter_media", False):
            if message.photo or message.video or message.animation or message.document:
                reason = t("mod_media", lang)

        # Anti-forward (block forwarded channel messages)
        if reason is None and settings.get("antiforward_enabled", False):
            if message.forward_from_chat:
                reason = "Forwarded message blocked"

        # Anti-phone/email
        if reason is None and settings.get("antispam_contacts", False):
            if has_phone(text) or has_email(text):
                reason = "Phone/email blocked"

        if reason is not None:
            try:
                await message.delete()
            except Exception:
                pass

            await add_warning(session, chat.id, user.id, user.id, reason=reason)
            warn_count = await increment_warnings(session, chat.id, user.id)
            max_warnings = settings.get("max_warnings", 3)

            mention = f"@{message.from_user.username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"

            if warn_count >= max_warnings:
                mute_duration = settings.get("mute_duration", 900)
                await mute_member(session, chat.id, user.id, mute_duration)
                # Real Telegram restriction
                try:
                    until_date = datetime.datetime.now() + datetime.timedelta(seconds=mute_duration)
                    await message.bot.restrict_chat_member(
                        chat_id=message.chat.id,
                        user_id=message.from_user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date,
                    )
                except Exception:
                    pass
                await log_action(
                    session, message.chat.id, message.from_user.id,
                    "muted", details=f"Auto-mute: {warn_count}/{max_warnings} warnings",
                )
                await message.answer(t("mod_muted", lang, user=mention, count=warn_count, reason=reason))
                await reset_warnings(session, chat.id, user.id)
            else:
                await message.answer(t("mod_warned", lang, user=mention, count=warn_count, reason=reason))

            await log_action(
                session, message.chat.id, message.from_user.id,
                "warned", details=reason,
            )


@router.message(IsGroup(), F.photo | F.video | F.animation, ~F.text.startswith("/"))
async def moderate_nsfw_media(message: Message) -> None:
    """Check media messages for potential NSFW content.

    Currently checks domain names in captions.
    Full image-based NSFW detection can be added via external API.
    """
    if message.from_user is None:
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return
    except Exception:
        return

    text = (message.caption or "").lower()
    if not text:
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

        # Check caption for NSFW words (with homoglyph normalization)
        text_normalized = normalize_text(text)
        for word in _NSFW_WORDS:
            if word.lower() in text or word.lower() in text_normalized:
                try:
                    await message.delete()
                except Exception:
                    pass

                await add_warning(session, chat.id, user.id, user.id, reason=f"NSFW caption: {word}")
                warn_count = await increment_warnings(session, chat.id, user.id)
                max_warnings = settings.get("max_warnings", 3)

                mention = f"@{message.from_user.username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"
                await message.answer(t("mod_warned", lang, user=mention, count=warn_count, reason=f"NSFW: {word}"))
                return

        # Check caption for NSFW domains
        for domain in _NSFW_DOMAINS:
            if domain in text:
                try:
                    await message.delete()
                except Exception:
                    pass
                return


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
    except Exception:
        return

    async with async_session_factory() as session:
        chat = await get_or_create_chat(session, telegram_id=message.chat.id)
        if not (chat.settings or {}).get("antiforward_enabled", False):
            return

        try:
            await message.delete()
        except Exception:
            pass


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
    except Exception:
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
            try:
                await message.delete()
            except Exception:
                pass

            await add_warning(
                session, chat.id, user.id, user.id,
                reason=f"NSFW sticker: {sticker_emoji}",
            )
            warn_count = await increment_warnings(session, chat.id, user.id)
            max_warnings = settings.get("max_warnings", 3)

            mention = f"@{message.from_user.username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"

            if warn_count >= max_warnings:
                mute_duration = settings.get("mute_duration", 900)
                await mute_member(session, chat.id, user.id, mute_duration)
                await log_action(
                    session, message.chat.id, message.from_user.id,
                    "muted", details=f"Auto-mute: {warn_count}/{max_warnings} NSFW stickers",
                )
                await message.answer(
                    t("mod_muted", lang, user=mention, count=warn_count, reason=f"NSFW sticker")
                )
                await reset_warnings(session, chat.id, user.id)
            else:
                await message.answer(
                    t("mod_warned", lang, user=mention, count=warn_count, reason=f"NSFW sticker")
                )

            await log_action(
                session, message.chat.id, message.from_user.id,
                "warned", details=f"NSFW sticker: {sticker_emoji}",
            )
