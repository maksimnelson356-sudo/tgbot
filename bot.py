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
        BotCommand(command="start", description="Start / Главная"),
        BotCommand(command="help", description="Help / Помощь"),
        BotCommand(command="language", description="Language / Язык"),
        BotCommand(command="panel", description="Mini App panel 🖥"),
        BotCommand(command="admin", description="Admin panel ⚙️"),
        BotCommand(command="warn", description="Warn a user ⚠️"),
        BotCommand(command="unwarn", description="Remove warning ✅"),
        BotCommand(command="mute", description="Mute a user 🔇"),
        BotCommand(command="ban", description="Ban a user 🔨"),
        BotCommand(command="unmute", description="Unmute a user 🔊"),
        BotCommand(command="warnings", description="List warnings 📋"),
        BotCommand(command="music", description="Search music 🎵"),
        BotCommand(command="rps", description="Rock-Paper-Scissors 🪨"),
        BotCommand(command="dice", description="Roll dice 🎲"),
        BotCommand(command="dart", description="Throw dart 🎯"),
        BotCommand(command="bowling", description="Bowling 🎳"),
        BotCommand(command="guess", description="Guess the number 🔢"),
        BotCommand(command="trivia", description="Trivia quiz 🧠"),
        BotCommand(command="joke", description="Random joke 😂"),
        BotCommand(command="fact", description="Random fact 🧠"),
        BotCommand(command="roll", description="Random number 🎲"),
        BotCommand(command="hug", description="Hug someone 🤗"),
        BotCommand(command="top", description="Leaderboard 🏆"),
        BotCommand(command="stats", description="Your stats 📊"),
    ]

    # ── Groups — regular users see only these ──────────────────────────
    user_group_commands = [
        BotCommand(command="music", description="Search music 🎵"),
        BotCommand(command="id", description="Show IDs 🆔"),
        BotCommand(command="info", description="User info 👤"),
        BotCommand(command="report", description="Report message 🚨"),
        BotCommand(command="calladmin", description="Call admins 🚨"),
        BotCommand(command="gift", description="Подарить партнёру 🎁"),
        BotCommand(command="familytop", description="Топ семей 💍"),
        BotCommand(command="marry", description="Браки 💍"),
        BotCommand(command="unmarry", description="Развод 💔"),
        BotCommand(command="marriage", description="Мой брак 💍"),
        BotCommand(command="rate", description="Поставить репутацию ⭐"),
        BotCommand(command="rep", description="Моя репутация ⭐"),
        BotCommand(command="toprep", description="Топ репутации 🏆"),
        BotCommand(command="rules", description="Чат правила 📜"),
        BotCommand(command="profile", description="Профиль 👤"),
        BotCommand(command="rank", description="Мой уровень 🏅"),
        BotCommand(command="daily", description="Ежедневный бонус 🎁"),
        BotCommand(command="topxp", description="Топ по опыту 🏆"),
        BotCommand(command="inviters", description="Топ приглашателей 🫂"),
        BotCommand(command="remind", description="Напоминание ⏰"),
        BotCommand(command="topact", description="Топ активности 🔥"),
        BotCommand(command="joke", description="Random joke 😂"),
        BotCommand(command="fact", description="Random fact 🧠"),
        BotCommand(command="weather", description="Weather 🌤"),
        BotCommand(command="feedback", description="Feedback to owner 💬"),
        BotCommand(command="birthdays", description="View birthdays 🎉"),
        BotCommand(command="setbday", description="Set birthday 🎂"),
    ]

    # ── Groups — admin-only commands ───────────────────────────────────
    admin_group_commands = [
        BotCommand(command="admin", description="Admin panel ⚙️"),
        BotCommand(command="panel", description="Mini App panel 🖥"),
        BotCommand(command="warn", description="Warn a user ⚠️"),
        BotCommand(command="unwarn", description="Remove warning ✅"),
        BotCommand(command="mute", description="Mute a user 🔇"),
        BotCommand(command="unmute", description="Unmute a user 🔊"),
        BotCommand(command="ban", description="Ban a user 🔨"),
        BotCommand(command="warnings", description="List warnings 📋"),
        BotCommand(command="pin", description="Pin message 📌"),
        BotCommand(command="unpin", description="Unpin message 📌"),
        BotCommand(command="admins", description="List admins 👑"),
        BotCommand(command="mutelist", description="Muted users 🔇"),
        BotCommand(command="clean", description="Delete bot messages 🧹"),
        BotCommand(command="allowlink", description="Whitelist domain ✅"),
        BotCommand(command="slowmode", description="Set slow mode 🐌"),
        BotCommand(command="addadmin", description="Назначить админа ➕"),
        BotCommand(command="removeadmin", description="Понизить админа ➖"),
        BotCommand(command="adminlist", description="Bot admins list 📋"),
        BotCommand(command="daystats", description="Today's stats 📊"),
        BotCommand(command="schedule", description="Scheduled post 📅"),
        BotCommand(command="schedule_list", description="List schedules 📋"),
        BotCommand(command="schedule_del", description="Delete schedule ❌"),
        BotCommand(command="addreply", description="Add auto-reply 📝"),
        BotCommand(command="listreplies", description="List auto-replies 📋"),
        BotCommand(command="purge", description="Delete messages 🗑️"),
        BotCommand(command="note", description="Add note 📝"),
        BotCommand(command="notes", description="List notes 📋"),
        BotCommand(command="delnote", description="Delete note ❌"),
        BotCommand(command="zombies", description="Clean dead accounts 🧟"),
        BotCommand(command="bansticker", description="Ban sticker set 🚫"),
    ]

    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(user_group_commands, scope=BotCommandScopeAllGroupChats())
    logger.info("Bot commands set (private=%d, group_user=%d)",
                len(private_commands), len(user_group_commands))


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
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # ── Auto-delete bot messages in groups (15s) ─────────────────────────
    from aiogram.types import Message as _Msg
    from utils.helpers import schedule_delete as _schedule_delete

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
