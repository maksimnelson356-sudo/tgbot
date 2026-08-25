import json

from aiogram import Router, F
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_chat, update_chat_settings
from filters.admin import HasRank
from filters.chat_type import IsGroup
from utils.helpers import escape_html
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "webapp"


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    """Handle data sent from the Mini App (opened from a DM panel button).

    The panel sends {"action": "toggle", "key": ..., "value": ...,
    "chat_id": <target group telegram_id>}. Settings must be applied to
    that target group — never to the DM chat itself.
    """
    if message.from_user is None or message.web_app_data is None:
        return

    lang = await get_user_lang(message)

    try:
        data = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        await message.answer("Ошибка данных.")
        return

    target_chat_tg_id = data.get("chat_id")
    if not isinstance(target_chat_tg_id, int):
        await message.answer("Не указан чат для применения настройки.")
        return

    # Authorize against the TARGET group only.
    if not await _check_admin_for_chat(message.bot, message.from_user.id, target_chat_tg_id):
        await message.answer(t("panel_not_admin", lang))
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
        if key not in allowed_keys or not isinstance(value, bool):
            await message.answer("Неизвестная настройка.")
            return

        async with async_session_factory() as session:
            chat_db = await get_or_create_chat(
                session, telegram_id=target_chat_tg_id,
                title=None, chat_type="supergroup",
            )
            await update_chat_settings(session, chat_db.id, {key: value})

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
        label = t(label_map.get(key) or key, lang)
        title = getattr(chat_db, "title", None) or str(target_chat_tg_id)
        await message.answer(f"{label} → {escape_html(title)}: {status}")


async def _check_admin_for_chat(bot, user_tg_id: int, target_chat_tg_id: int) -> bool:
    """True only if the user is an admin of the TARGET group."""
    try:
        member = await bot.get_chat_member(target_chat_tg_id, user_tg_id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception:
        pass
    async with async_session_factory() as session:
        from db.queries import get_chat_admin_rank, get_or_create_user
        chat_db = await get_or_create_chat(
            session, telegram_id=target_chat_tg_id, chat_type="supergroup",
        )
        user = await get_or_create_user(session, telegram_id=user_tg_id)
        return await get_chat_admin_rank(session, chat_db.id, user.id) is not None
