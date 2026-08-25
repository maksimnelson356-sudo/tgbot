"""User profile handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import (
    get_or_create_chat,
    get_or_create_user,
    get_reputation,
    get_user_warnings,
    get_user_marriages,
)
from filters.chat_type import IsGroup
from utils.helpers import escape_html, keep_next
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "profile"


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    """Show user profile. Usage: /profile or /profile @reply"""
    lang = await get_user_lang(message)

    target = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=target.id)
        chat = await get_or_create_chat(session, telegram_id=message.chat.id) if message.chat else None

    lines = [
        f"👤 <b>{t('profile_title', lang)}</b>",
        f"├ {t('profile_name', lang)}: <b>{escape_html(target.first_name or '')} {escape_html(target.last_name or '')}</b>",
        f"├ {t('profile_username', lang)}: @{escape_html(target.username)}" if target.username else f"├ ID: {target.id}",
        f"├ {t('profile_id', lang)}: <code>{target.id}</code>",
        f"├ {t('profile_language', lang)}: {user.language or 'ru'}",
    ]

    # Marriage status
    async with async_session_factory() as session:
        marriages = await get_user_marriages(session, user.telegram_id)
        active = [m for m in marriages if m["status"] == "married"]

    if active:
        partner_id = active[0]["partner_id"]
        async with async_session_factory() as session:
            partner = await get_or_create_user(session, telegram_id=partner_id)
        partner_name = escape_html(partner.first_name or str(partner_id))
        married_date = active[0]["married_at"].strftime("%d.%m.%Y") if active[0]["married_at"] else "?"
        lines.append(f"├ 💍 {t('marry_partner', lang)}: <b>{partner_name}</b> ({married_date})")
    else:
        lines.append(f"├ 💔 {t('marry_single', lang)}")

    # Reputation
    if chat:
        async with async_session_factory() as session:
            rep = await get_reputation(session, chat.id, user.id)
        lines.append(f"├ ⭐ {t('profile_reputation', lang)}: {rep}")

    # Warnings
    if chat:
        async with async_session_factory() as session:
            warnings = await get_user_warnings(session, chat.id, user.id)
        lines.append(f"├ ⚠️ {t('profile_warnings', lang)}: {len(warnings)}")

    # Join date
    if user.created_at:
        lines.append(f"└ 📅 {t('profile_since', lang)}: {user.created_at.strftime('%d.%m.%Y')}")

    keep_next(message)
    await message.answer("\n".join(lines))
