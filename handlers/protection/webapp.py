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

    if not await _check_admin(message):
        lang = await get_user_lang(message)
        await message.answer(t("panel_not_admin", lang))
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
            "raid_mode_enabled", "antiforward_enabled",
            "antispam_contacts", "autoreplies_enabled", "ai_chat_enabled",
        }
        if key not in allowed_keys:
            await message.answer("Неизвестная настройка.")
            return

        async with async_session_factory() as session:
            chat_db = await get_or_create_chat(session, telegram_id=message.chat.id)
            await update_chat_settings(session, chat_db.id, {key: value})

        lang = await get_user_lang(message)
        status = t("on", lang) if value else t("off", lang)

        label_map = {
            "antispam_enabled": "admin_antispam",
            "moderation_enabled": "admin_moderation",
            "filter_links": "admin_links",
            "filter_media": "admin_media",
            "nsfw_filter_enabled": "admin_nsfw",
            "bad_words_enabled": "admin_badwords",
            "raid_mode_enabled": "admin_raid",
            "antiforward_enabled": "admin_antiforward",
            "antispam_contacts": "admin_contacts",
            "autoreplies_enabled": "admin_autoreplies",
            "ai_chat_enabled": "admin_ai_chat",
        }
        label = t(label_map.get(key, key), lang)
        await message.answer(f"{label}: {status}")


async def _check_admin(message: Message) -> bool:
    if message.chat.type in ("group", "supergroup"):
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
    else:
        async with async_session_factory() as session:
            from db.queries import get_user_any_admin_rank
            return await get_user_any_admin_rank(session, message.from_user.id)
