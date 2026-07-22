import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo

from config import settings
from db.base import init_db



logger = logging.getLogger(__name__)

_AUTO_DELETE_DELAY = 5.0  # seconds


async def _auto_delete_message(message: Message, delay: float) -> None:
    """Delete a message after a delay."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def set_bot_commands(bot: Bot) -> None:
    """Set bot commands visible in the menu."""
    from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

    # Commands for private chat (all commands)
    private_commands = [
        BotCommand(command="start", description="Start / Главная"),
        BotCommand(command="help", description="Help / Помощь"),
        BotCommand(command="language", description="Language / Язык"),
        BotCommand(command="rps", description="Rock-Paper-Scissors 🪨"),
        BotCommand(command="dice", description="Roll dice 🎲"),
        BotCommand(command="dart", description="Throw dart 🎯"),
        BotCommand(command="bowling", description="Bowling 🎳"),
        BotCommand(command="guess", description="Guess the number 🔢"),
        BotCommand(command="trivia", description="Trivia quiz 🧠"),
        BotCommand(command="joke", description="Random joke 😂"),
        BotCommand(command="fact", description="Random fact 🧠"),
        BotCommand(command="music", description="Search music 🎵"),
        BotCommand(command="roll", description="Random number 🎲"),
        BotCommand(command="hug", description="Hug someone 🤗"),
        BotCommand(command="top", description="Leaderboard 🏆"),
        BotCommand(command="stats", description="Your stats 📊"),
    ]

    # Commands for groups (only group-relevant)
    group_commands = [
        BotCommand(command="admin", description="Admin panel ⚙️"),
        BotCommand(command="panel", description="Mini App panel 🖥"),
        BotCommand(command="warn", description="Warn a user ⚠️"),
        BotCommand(command="unwarn", description="Remove warning ✅"),
        BotCommand(command="mute", description="Mute a user 🔇"),
        BotCommand(command="ban", description="Ban a user 🔨"),
        BotCommand(command="unmute", description="Unmute a user 🔊"),
        BotCommand(command="warnings", description="List warnings 📋"),
        BotCommand(command="id", description="Show IDs 🆔"),
        BotCommand(command="info", description="User info 👤"),
        BotCommand(command="report", description="Report message 🚨"),
        BotCommand(command="calladmin", description="Call admins 🚨"),
        BotCommand(command="rate", description="Give reputation ⭐"),
        BotCommand(command="rep", description="Check reputation ⭐"),
        BotCommand(command="toprep", description="Reputation top 🏆"),
        BotCommand(command="rules", description="Chat rules 📜"),
        BotCommand(command="zombies", description="Clean dead accounts 🧟"),
        BotCommand(command="music", description="Search music 🎵"),
        BotCommand(command="pin", description="Pin message 📌"),
        BotCommand(command="unpin", description="Unpin message 📌"),
        BotCommand(command="admins", description="List admins 👑"),
        BotCommand(command="mutelist", description="Muted users 🔇"),
        BotCommand(command="clean", description="Delete bot messages 🧹"),
        BotCommand(command="allowlink", description="Whitelist domain ✅"),
        BotCommand(command="slowmode", description="Set slow mode 🐌"),
        BotCommand(command="weather", description="Weather 🌤"),
        BotCommand(command="feedback", description="Feedback to owner 💬"),
        BotCommand(command="addadmin", description="Назначить админа ➕"),
        BotCommand(command="removeadmin", description="Понизить админа ➖"),
        BotCommand(command="adminlist", description="Bot admins list 📋"),
        BotCommand(command="daystats", description="Today's stats 📊"),
        BotCommand(command="schedule", description="Scheduled post 📅"),
        BotCommand(command="schedule_list", description="List schedules 📋"),
        BotCommand(command="schedule_del", description="Delete schedule ❌"),
        BotCommand(command="addreply", description="Add auto-reply 📝"),
        BotCommand(command="listreplies", description="List auto-replies 📋"),
        BotCommand(command="setbday", description="Set birthday 🎂"),
        BotCommand(command="birthdays", description="View birthdays 🎉"),
        BotCommand(command="purge", description="Delete messages 🗑️"),
        BotCommand(command="note", description="Add note 📝"),
        BotCommand(command="notes", description="List notes 📋"),
        BotCommand(command="delnote", description="Delete note ❌"),
        BotCommand(command="language", description="Language / Язык"),
        BotCommand(command="rps", description="Rock-Paper-Scissors 🪨"),
        BotCommand(command="dice", description="Roll dice 🎲"),
        BotCommand(command="dart", description="Throw dart 🎯"),
        BotCommand(command="bowling", description="Bowling 🎳"),
        BotCommand(command="guess", description="Guess the number 🔢"),
        BotCommand(command="trivia", description="Trivia quiz 🧠"),
        BotCommand(command="joke", description="Random joke 😂"),
        BotCommand(command="fact", description="Random fact 🧠"),
        BotCommand(command="music", description="Search music 🎵"),
        BotCommand(command="roll", description="Random number 🎲"),
        BotCommand(command="hug", description="Hug someone 🤗"),
        BotCommand(command="top", description="Leaderboard 🏆"),
        BotCommand(command="stats", description="Your stats 📊"),
    ]

    await bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    logger.info("Bot commands set")


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

    # Set WebApp menu button for all chats
    await set_menu_buttons(bot)


async def on_shutdown(bot: Bot) -> None:
    """Cleanup on shutdown."""
    logger.info("Bot shutting down...")


async def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Wrap send_message to auto-delete bot messages in groups after 5s
    _original_send_message = bot.send_message

    async def _auto_delete_send_message(*args, **kwargs):
        result = await _original_send_message(*args, **kwargs)
        chat_id = kwargs.get("chat_id") or (args[0] if args else None)
        if chat_id and str(chat_id).startswith("-"):
            # Skip inline keyboards — user needs time to click
            if not kwargs.get("reply_markup"):
                asyncio.create_task(_auto_delete_message(result, _AUTO_DELETE_DELAY))
        return result

    bot.send_message = _auto_delete_send_message  # type: ignore

    dp = Dispatcher()

    # Register lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

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

    # ── Register routers ─────────────────────────────────────────────────
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
    dp.include_router(antispam_router)
    dp.include_router(moderation_router)

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
