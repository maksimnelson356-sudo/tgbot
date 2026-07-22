import json

from aiogram import Router, F
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, update_chat_settings
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "webapp"


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    """Handle data sent from the Mini App."""
    if message.from_user is None:
        return

    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта панель работает только в группах.")
        return

    if not await _check_admin(message):
        await message.answer("Только админы могут управлять настройками.")
        return

    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        await message.answer("Ошибка данных.")
        return

    if data.get("action") == "toggle":
        key = data.get("key")
        value = data.get("value")

        if key is None or value is None:
            await message.answer("Неверные данные.")
            return

        allowed_keys = {
            "antispam_enabled", "moderation_enabled", "filter_links",
            "filter_media", "nsfw_filter_enabled", "bad_words_enabled",
            "captcha_enabled", "raid_mode_enabled",
        }
        if key not in allowed_keys:
            await message.answer("Неизвестная настройка.")
            return

        async with async_session_factory() as session:
            await update_chat_settings(session, message.chat.id, {key: value})

        lang = await get_user_lang(message)
        status = t("on", lang) if value else t("off", lang)

        label_map = {
            "antispam_enabled": "admin_antispam",
            "moderation_enabled": "admin_moderation",
            "filter_links": "admin_links",
            "filter_media": "admin_media",
            "nsfw_filter_enabled": "admin_nsfw",
            "bad_words_enabled": "admin_badwords",
            "captcha_enabled": "admin_captcha",
            "raid_mode_enabled": "admin_raid",
        }
        label = t(label_map.get(key, key), lang)
        await message.answer(f"{label}: {status}")


async def _check_admin(message: Message) -> bool:
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception:
        pass
    async with async_session_factory() as session:
        from db.queries import get_chat_admin_rank
        chat_db = await get_or_create_chat(session, telegram_id=message.chat.id)
        from db.queries import get_or_create_user
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        return await get_chat_admin_rank(session, chat_db.id, user.id) is not None
