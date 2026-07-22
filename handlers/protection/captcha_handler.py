from aiogram import Router, F
from aiogram.types import ChatPermissions, Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, log_action
from filters.chat_type import IsGroup
from services.captcha import create_challenge, verify, has_pending, _pending
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "captcha_handler"

FULL_PERMISSIONS = ChatPermissions(
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


async def send_captcha(chat_id: int, user_id: int, bot) -> None:
    """Send CAPTCHA challenge to a chat for a new user."""
    _answer, image = create_challenge(chat_id, user_id)

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
        )
    except Exception:
        pass

    await bot.send_photo(
        chat_id=chat_id,
        photo=image,
        caption=t("captcha_prompt", "ru"),
    )


@router.message(IsGroup(), F.text, ~F.text.startswith("/"))
async def on_captcha_answer(message: Message) -> None:
    """Catch text from users with pending CAPTCHA (no FSM needed)."""
    if message.from_user is None or message.text is None:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not has_pending(chat_id, user_id):
        return

    lang = await get_user_lang(message)
    result = verify(chat_id, user_id, message.text.strip())

    if result is True:
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await message.chat.restrict_chat_member(
                user_id=user_id,
                permissions=FULL_PERMISSIONS,
            )
        except Exception:
            pass

        async with async_session_factory() as session:
            chat_db = await get_or_create_chat(session, telegram_id=chat_id)
            await log_action(session, chat_id, user_id, "captcha_passed")

        name = message.from_user.first_name or message.from_user.username or str(user_id)
        await message.answer(t("captcha_passed", lang, name=name))

    elif result is False:
        try:
            await message.delete()
        except Exception:
            pass

        info = _pending.get((chat_id, user_id))
        name = message.from_user.first_name or "?"

        if info is None or info.get("attempts", 0) >= 3:
            await message.answer(t("captcha_too_many", lang, name=name))
            try:
                await message.chat.ban_chat_member(user_id)
                await message.chat.unban_chat_member(user_id)
            except Exception:
                pass
        else:
            remaining = 3 - info.get("attempts", 0)
            await message.answer(t("captcha_wrong", lang, name=name, attempts=remaining))

    else:
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(t("captcha_expired", lang))
        try:
            await message.chat.ban_chat_member(user_id)
            await message.chat.unban_chat_member(user_id)
        except Exception:
            pass
