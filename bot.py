import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import settings
from db.base import init_db



logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Set bot commands visible in the menu."""
    from aiogram.types import (
        BotCommand, BotCommandScopeDefault,
        BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators,
    )

    # ── Private chat (all commands) ────────────────────────────────────
    private_commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="language", description="Язык"),
        BotCommand(command="panel", description="Панель приложения 🖥"),
        BotCommand(command="admin", description="Панель админа ⚙️"),
        BotCommand(command="warn", description="Предупредить ⚠️"),
        BotCommand(command="unwarn", description="Снять предупреждение ✅"),
        BotCommand(command="mute", description="Замутить 🔇"),
        BotCommand(command="ban", description="Забанить 🔨"),
        BotCommand(command="unmute", description="Размутить 🔊"),
        BotCommand(command="warnings", description="Список предупреждений 📋"),
        BotCommand(command="music", description="Поиск музыки 🎵"),
        BotCommand(command="rps", description="Камень-Ножницы-Бумага 🪨"),
        BotCommand(command="dice", description="Бросить кубик 🎲"),
        BotCommand(command="dart", description="Бросить дротик 🎯"),
        BotCommand(command="bowling", description="Боулинг 🎳"),
        BotCommand(command="guess", description="Угадай число 🔢"),
        BotCommand(command="trivia", description="Викторина 🧠"),
        BotCommand(command="joke", description="Случайная шутка 😂"),
        BotCommand(command="fact", description="Случайный факт 🧠"),
        BotCommand(command="roll", description="Случайное число 🎲"),
        BotCommand(command="hug", description="Обнять 🤗"),
        BotCommand(command="top", description="Таблица лидеров 🏆"),
        BotCommand(command="stats", description="Твоя статистика 📊"),
    ]

    # ── Groups — regular users see only these ──────────────────────────
    user_group_commands = [
        BotCommand(command="music", description="Поиск музыки 🎵"),
        BotCommand(command="id", description="Показать ID 🆔"),
        BotCommand(command="info", description="Информация о пользователе 👤"),
        BotCommand(command="report", description="Пожаловаться 🚨"),
        BotCommand(command="calladmin", description="Позвать админа 🚨"),
        BotCommand(command="gift", description="Подарить партнёру 🎁"),
        BotCommand(command="familytop", description="Топ семей 💍"),
        BotCommand(command="marry", description="Браки 💍"),
        BotCommand(command="unmarry", description="Развод 💔"),
        BotCommand(command="marriage", description="Мой брак 💍"),
        BotCommand(command="rate", description="Поставить репутацию ⭐"),
        BotCommand(command="rep", description="Моя репутация ⭐"),
        BotCommand(command="toprep", description="Топ репутации 🏆"),
        BotCommand(command="rules", description="Правила чата 📜"),
        BotCommand(command="profile", description="Профиль 👤"),
        BotCommand(command="rank", description="Мой уровень 🏅"),
        BotCommand(command="daily", description="Ежедневный бонус 🎁"),
        BotCommand(command="topxp", description="Топ по опыту 🏆"),
        BotCommand(command="inviters", description="Топ приглашателей 🫂"),
        BotCommand(command="remind", description="Напоминание ⏰"),
        BotCommand(command="topact", description="Топ активности 🔥"),
        BotCommand(command="joke", description="Случайная шутка 😂"),
        BotCommand(command="fact", description="Случайный факт 🧠"),
        BotCommand(command="weather", description="Погода 🌤"),
        BotCommand(command="feedback", description="Написать владельцу 💬"),
        BotCommand(command="birthdays", description="Дни рождения 🎉"),
        BotCommand(command="setbday", description="Установить дату рождения 🎂"),
    ]

    # ── Groups — admin-only commands ───────────────────────────────────
    admin_group_commands = [
        BotCommand(command="admin", description="Панель админа ⚙️"),
        BotCommand(command="panel", description="Панель приложения 🖥"),
        BotCommand(command="warn", description="Предупредить ⚠️"),
        BotCommand(command="unwarn", description="Снять предупреждение ✅"),
        BotCommand(command="mute", description="Замутить 🔇"),
        BotCommand(command="unmute", description="Размутить 🔊"),
        BotCommand(command="ban", description="Забанить 🔨"),
        BotCommand(command="warnings", description="Список предупреждений 📋"),
        BotCommand(command="pin", description="Закрепить 📌"),
        BotCommand(command="unpin", description="Открепить 📌"),
        BotCommand(command="admins", description="Список админов 👑"),
        BotCommand(command="mutelist", description="Замученные 🔇"),
        BotCommand(command="clean", description="Очистить сообщения 🧹"),
        BotCommand(command="allowlink", description="Разрешить ссылку ✅"),
        BotCommand(command="slowmode", description="Медленный режим 🐌"),
        BotCommand(command="addadmin", description="Назначить админа ➕"),
        BotCommand(command="removeadmin", description="Понизить админа ➖"),
        BotCommand(command="adminlist", description="Админы бота 📋"),
        BotCommand(command="daystats", description="Статистика дня 📊"),
        BotCommand(command="schedule", description="Запланированный пост 📅"),
        BotCommand(command="schedule_list", description="Список рассылок 📋"),
        BotCommand(command="schedule_del", description="Удалить рассылку ❌"),
        BotCommand(command="addreply", description="Добавить автоответ 📝"),
        BotCommand(command="listreplies", description="Список автоответов 📋"),
        BotCommand(command="purge", description="Удалить сообщения 🗑️"),
        BotCommand(command="note", description="Добавить заметку 📝"),
        BotCommand(command="notes", description="Список заметок 📋"),
        BotCommand(command="delnote", description="Удалить заметку ❌"),
        BotCommand(command="zombies", description="Очистить мёртвых 🧟"),
        BotCommand(command="bansticker", description="Забанить стикер 🚫"),
        BotCommand(command="setrules", description="Установить правила 📜"),
        BotCommand(command="delrules", description="Удалить правила 📜"),
        BotCommand(command="logs", description="Логи действий 📋"),
        BotCommand(command="addword", description="Добавить слово 🚫"),
        BotCommand(command="delword", description="Удалить слово 🚫"),
        BotCommand(command="badwords", description="Чёрный список 📝"),
        BotCommand(command="banhistory", description="История банов 📋"),
        BotCommand(command="setantispam", description="Антиспам ⚙️"),
        BotCommand(command="setslowmode", description="Медленный режим 🐌"),
    ]

    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(user_group_commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(admin_group_commands, scope=BotCommandScopeAllChatAdministrators())
    logger.info("Bot commands set (private=%d, group_user=%d, group_admin=%d)",
                len(private_commands), len(user_group_commands), len(admin_group_commands))


PANEL_URL = "https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html"


async def set_menu_buttons(bot: Bot) -> None:
    """Set the WebApp menu button — default for all chats."""
    menu_button = MenuButtonWebApp(text="⚙️ Панель", web_app=WebAppInfo(url=PANEL_URL))

    try:
        result = await bot.set_chat_menu_button(menu_button=menu_button)
        logger.info("Default menu button set: %s", result)
    except Exception as e:
        logger.warning("Failed to set default menu button: %s", e)


async def on_startup(bot: Bot) -> None:
    """Initialize database and notify admins."""
    await init_db()
    logger.info("Database initialized")

    # Set bot username after start
    me = await bot.get_me()
    settings.BOT_USERNAME = me.username or ""

    # Set commands
    await set_bot_commands(bot)
    logger.info("Bot started: @%s (id: %s)", me.username, me.id)

    # Start scheduler
    from services.scheduler_service import start_scheduler
    start_scheduler(bot)

    # Start Telethon client (for /zombies, member scanning)
    from services.telethon_client import get_client
    await get_client()

    # Start auto-unmute background task
    from handlers.protection.utilities import auto_unmute_check
    from utils.helpers import spawn
    spawn(auto_unmute_check(bot), name="auto_unmute_loop")
    logger.info("Auto-unmute task started")

    # Set WebApp menu button for all chats
    await set_menu_buttons(bot)


async def on_shutdown(bot: Bot) -> None:
    """Cleanup on shutdown."""
    from services.telethon_client import stop_client
    from services.scheduler_service import stop_scheduler
    from utils.helpers import shutdown_background_tasks
    stop_scheduler()
    await shutdown_background_tasks()
    await stop_client()
    logger.info("Bot shutting down...")


async def on_error(event) -> None:
    """Global error handler — log any unhandled exception from handlers."""
    logger.error(
        "Unhandled exception while processing update %s",
        getattr(event, "update", event),
        exc_info=getattr(event, "exception", None),
    )


async def main() -> None:
    """Main entry point."""
    import sys
    import os

    # Check .env file exists
    if not os.path.exists(".env"):
        logger.warning(".env file not found — using environment variables only")

    # Validate critical settings
    if not getattr(settings, "BOT_TOKEN", None):
        logger.error("BOT_TOKEN is missing — aborting startup")
        sys.exit(1)

    if not getattr(settings, "DATABASE_URL", None):
        logger.error("DATABASE_URL is missing — aborting startup")
        sys.exit(1)

    # Warn on optional but important settings
    if not getattr(settings, "GOOGLE_API_KEY", None):
        logger.warning("GOOGLE_API_KEY is missing — AI moderation and AI chat will be disabled")

    if not getattr(settings, "TELETHON_API_ID", None) or not getattr(settings, "TELETHON_API_HASH", None):
        logger.warning("TELETHON credentials missing — /zombies and member scanning will be disabled")

    # Config status report
    logger.info("=== Bot Configuration ===")
    logger.info("BOT_TOKEN: %s", "SET" if settings.BOT_TOKEN else "MISSING")
    logger.info("DATABASE_URL: %s", "SET" if settings.DATABASE_URL else "MISSING")
    logger.info("GOOGLE_API_KEY: %s", "SET" if settings.GOOGLE_API_KEY else "MISSING (AI disabled)")
    logger.info("TELETHON_API_ID: %s", "SET" if settings.TELETHON_API_ID else "MISSING")
    logger.info("TELETHON_API_HASH: %s", "SET" if settings.TELETHON_API_HASH else "MISSING")
    logger.info("OWNER_ID: %s", settings.OWNER_ID if settings.OWNER_ID else "NOT SET")
    logger.info("LOG_LEVEL: %s", settings.LOG_LEVEL)
    logger.info("==========================")

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# ── Auto-delete bot messages in groups (15s) ─────────────────────────
    try:
        from aiogram.types import Message as _Msg
        from utils.helpers import schedule_delete as _schedule_delete

        # Version check: verify Message class has expected attributes
        if not hasattr(_Msg, 'answer') or not hasattr(_Msg, 'reply'):
            raise AttributeError("Message class missing required methods")

        _orig_answer = _Msg.answer
        _orig_reply = _Msg.reply
        _MEDIA_ATTRS = ("audio", "video", "photo", "animation", "document",
                         "voice", "video_note", "sticker")

        def _should_auto_delete(result) -> bool:
            return bool(
                result and result.chat.type in ("group", "supergroup")
                and not result.reply_markup
                and not any(getattr(result, attr, None) for attr in _MEDIA_ATTRS)
            )

        async def _auto_del_answer(self, *a, **kw):
            # A handler may request a longer TTL via helpers.keep_next(msg, delay)
            override = getattr(self, "_autodel_delay", None)
            if override is not None:
                try:
                    del self._autodel_delay
                except AttributeError:
                    pass
            result = await _orig_answer(self, *a, **kw)
            if _should_auto_delete(result):
                _schedule_delete(result, float(override) if override else 15.0)
            return result

        async def _auto_del_reply(self, *a, **kw):
            override = getattr(self, "_autodel_delay", None)
            if override is not None:
                try:
                    del self._autodel_delay
                except AttributeError:
                    pass
            result = await _orig_reply(self, *a, **kw)
            if _should_auto_delete(result):
                _schedule_delete(result, float(override) if override else 15.0)
            return result

        _Msg.answer = _auto_del_answer
        _Msg.reply = _auto_del_reply
        logger.info("Auto-delete patched: bot messages in groups will expire in 15s")
    except Exception as e:
        logger.warning("Auto-delete monkey-patch failed, bot will run without auto-delete: %s", e)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Register lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.errors.register(on_error)

    # Register reaction handler
    from handlers.reactions import on_reaction
    dp.update.register(on_reaction)

    # ── Import and register routers ──────────────────────────────────────
    from handlers.start import router as start_router
    from handlers.protection.antispam import router as antispam_router
    from handlers.protection.captcha_handler import router as captcha_router
    from handlers.protection.moderation import router as moderation_router
    from handlers.protection.warnings import router as warnings_router
    from handlers.protection.admin_panel import router as admin_panel_router
    from handlers.entertainment.games import router as games_router
    from handlers.entertainment.fun import router as fun_router
    from handlers.entertainment.leaderboard import router as leaderboard_router
    from handlers.language import router as language_router
    from handlers.protection.info import router as info_router
    from handlers.protection.report import router as report_router
    from handlers.protection.purge import router as purge_router
    from handlers.protection.notes import router as notes_router
    from handlers.protection.reputation import router as reputation_router
    from handlers.protection.bansticker import router as bansticker_router
    from handlers.protection.rules import router as rules_router
    from handlers.protection.zombies import router as zombies_router
    from handlers.protection.autoresponder import router as autoresponder_router
    from handlers.protection.slowmode_cmd import router as slowmode_cmd_router
    from handlers.protection.stats_daily import router as stats_daily_router
    from handlers.protection.birthdays import router as birthdays_router
    from handlers.entertainment.weather import router as weather_router
    from handlers.entertainment.music import router as music_router
    from handlers.feedback import router as feedback_router
    from handlers.protection.setlog import router as setlog_router
    from handlers.protection.utilities import router as utilities_router
    from handlers.protection.scheduler import router as scheduler_router
    from handlers.protection.webapp import router as webapp_router
    from handlers.protection.ai_chat import router as ai_chat_router
    from handlers.relationships import router as relationships_router
    from handlers.profile import router as profile_router
    from handlers.remind import router as remind_router
    from handlers.xp import router as xp_router
    from handlers.entertainment.inline import router as inline_router

    # ── Register middlewares ──────────────────────────────────────────────
    from middlewares.throttling import ThrottlingMiddleware
    from middlewares.logging import LoggingMiddleware
    from middlewares.auto_delete import AutoDeleteCommandsMiddleware
    from middlewares.slowmode import SlowModeMiddleware

    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(AutoDeleteCommandsMiddleware())
    dp.message.middleware(SlowModeMiddleware())
    dp.chat_join_request.middleware(LoggingMiddleware())

    # ── Register routers ─────────────────────────────────────────
    # ORDER MATTERS:
    # - music_router, ai_chat_router, captcha_router: handle specific text (FSM, replies, pending captcha)
    # - autoresponder_router: catches text for auto-replies
    # - moderation_router: catches ALL remaining group text — MUST BE LAST
    dp.include_router(start_router)
    dp.include_router(music_router)
    dp.include_router(ai_chat_router)
    dp.include_router(captcha_router)
    dp.include_router(admin_panel_router)
    dp.include_router(warnings_router)
    dp.include_router(games_router)
    dp.include_router(fun_router)
    dp.include_router(leaderboard_router)
    dp.include_router(info_router)
    dp.include_router(language_router)
    dp.include_router(report_router)
    dp.include_router(purge_router)
    dp.include_router(notes_router)
    dp.include_router(reputation_router)
    dp.include_router(bansticker_router)
    dp.include_router(rules_router)
    dp.include_router(zombies_router)
    dp.include_router(autoresponder_router)
    dp.include_router(slowmode_cmd_router)
    dp.include_router(stats_daily_router)
    dp.include_router(birthdays_router)
    dp.include_router(weather_router)
    dp.include_router(feedback_router)
    dp.include_router(setlog_router)
    dp.include_router(utilities_router)
    dp.include_router(scheduler_router)
    dp.include_router(webapp_router)
    dp.include_router(profile_router)
    dp.include_router(remind_router)
    dp.include_router(xp_router)
    dp.include_router(relationships_router)
    dp.include_router(antispam_router)
    dp.include_router(moderation_router)
    dp.include_router(inline_router)

    # Explicit allowed_updates: without message_reaction Telegram never
    # delivers reaction updates (default excludes them), killing the rep system.
    ALLOWED_UPDATES = [
        "message",
        "edited_message",
        "callback_query",
        "chat_member",
        "my_chat_member",
        "chat_join_request",
        "message_reaction",
        "message_reaction_count",
    ]

    logger.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


if __name__ == "__main__":
    asyncio.run(main())
