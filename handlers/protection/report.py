from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat
from filters.chat_type import IsGroup
from utils.helpers import escape_html
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "report"


@router.message(Command("report"), IsGroup())
async def cmd_report(message: Message) -> None:
    """Report a message to admins. Usage: /report <reply> [reason]"""
    if message.reply_to_message is None:
        await message.answer("Ответь на сообщение, на которое хочешь пожаловаться.")
        return

    lang = await get_user_lang(message)
    reason = message.text.removeprefix("/report").strip() or "Без причины"

    reported_msg = message.reply_to_message
    reporter = message.from_user
    if reporter is None:
        return
    reported_user = reported_msg.from_user

    # Build report text
    if reported_user:
        offender_line = f"👤 Нарушитель: {escape_html(reported_user.first_name)} (ID: {reported_user.id})"
    else:
        offender_line = "👤 Нарушитель: аноним/канал"

    report_text = (
        f"🚨 <b>Жалоба!</b>\n\n"
        f"👤 От кого: {escape_html(reporter.first_name)} (ID: {reporter.id})\n"
        f"{offender_line}\n"
        f"📝 Причина: {escape_html(reason)}\n"
        f"💬 <a href='{reported_msg.get_url()}'>Перейти к сообщению</a>"
    )

    # Send report to chat (admins will see it)
    await message.answer(report_text)

    # Try to also DM all admins
    try:
        admins = await message.chat.get_administrators()
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await message.bot.send_message(
                        admin.user.id,
                        f"🚨 <b>Жалоба от {escape_html(reporter.first_name)}</b>\n\n{escape_html(reason)}\n\n"
                        f"Чат: {escape_html(message.chat.title)}\n"
                        f"<a href='{reported_msg.get_url()}'>Посмотреть сообщение</a>",
                    )
                except Exception:
                    pass
    except Exception:
        pass

    # Delete the command message
    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("calladmin"), IsGroup())
async def cmd_calladmin(message: Message) -> None:
    """Call all admins for help. Usage: /calladmin [reason]"""
    reason = message.text.removeprefix("/calladmin").strip() or "Нужна помощь!"

    # Mention all admins
    admin_mentions = []
    try:
        admins = await message.chat.get_administrators()
        for admin in admins:
            if not admin.user.is_bot:
                if admin.user.username:
                    admin_mentions.append(f"@{admin.user.username}")
                else:
                    admin_mentions.append(f"<b>{escape_html(admin.user.first_name)}</b>")
    except Exception:
        admin_mentions.append("Admins")

    mentions = " ".join(admin_mentions)

    # Get message context if replying
    context = ""
    if message.reply_to_message:
        url = message.reply_to_message.get_url()
        context = f"\n💬 <a href='{url}'>Сообщение для контекста</a>"

    await message.answer(
        f"🚨 <b>Вызов админа!</b>\n\n"
        f"👤 От: {escape_html(message.from_user.first_name)}\n"
        f"📝 Причина: {escape_html(reason)}"
        f"{context}\n\n"
        f"{mentions}",
    )

    # Also DM admins
    try:
        admins = await message.chat.get_administrators()
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await message.bot.send_message(
                        admin.user.id,
                        f"🚨 <b>Вызов админа в {escape_html(message.chat.title)}</b>\n\n"
                        f"👤 От: {escape_html(message.from_user.first_name)} (ID: {message.from_user.id})\n"
                        f"📝 Причина: {escape_html(reason)}",
                    )
                except Exception:
                    pass
    except Exception:
        pass
