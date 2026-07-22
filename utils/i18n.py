"""Internationalization — Russian / English language support."""

from typing import Optional

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        # Start / Help
        "start_welcome": (
            "👋 <b>Привет, {name}!</b>\n\n"
            "Я многофункциональный бот — защищаю чаты и развлекаю! 🛡️🎮\n\n"
            "<b>Команды:</b>\n\n"
            "🛡️ <b>Защита</b>\n"
            "  /admin — Панель администратора\n"
            "  /warn &lt;reply&gt; [причина] — Предупредить\n"
            "  /mute &lt;reply&gt; [время] — Замутить\n"
            "  /unmute &lt;reply&gt; — Размутить\n"
            "  /unwarn &lt;reply&gt; — Снять предупреждение\n"
            "  /warnings &lt;reply&gt; — Список предупреждений\n\n"
            "🎮 <b>Игры</b>\n"
            "  /rps — Камень-ножницы-бумага 🪨📄✂️\n"
            "  /dice — Бросить кубик 🎲\n"
            "  /dart — Дротик 🎯\n"
            "  /bowling — Боулинг 🎳\n"
            "  /guess — Угадай число 🔢\n"
            "  /trivia — Викторина 🧠\n\n"
            "😂 <b>Развлечения</b>\n"
            "  /joke — Шутка 😂\n"
            "  /fact — Факт 🧠\n"
            "  /music — Музыка 🎵\n"
            "  /roll — Случайное число 🎲\n\n"
            "📊 <b>Статистика</b>\n"
            "  /top — Таблица лидеров 🏆\n"
            "  /stats — Твоя статистика\n\n"
            "🌐 /language — Switch language / Сменить язык"
        ),
        "help_title": "❓ <b>Помощь</b> — нажми /start",
        "language_prompt": "🌐 <b>Выбери язык / Choose language:</b>",
        "language_set_ru": "✅ Язык установлен: <b>Русский</b>",
        "language_set_en": "✅ Language set: <b>English</b>",

        # Games
        "rps_title": "🪨📄✂️ <b>Камень-Ножницы-Бумага!</b>\nВыбери свой ход:",
        "rps_usage": "🪨📄✂️ <b>Камень-Ножницы-Бумага!</b>\n\nИспользование: /rps камень|бумага|ножницы\nИли: /rps rock|paper|scissors",
        "rps_user": "Ты",
        "rps_bot": "Бот",
        "rps_win": "🎉 Ты победил!",
        "rps_loss": "😢 Бот победил!",
        "rps_draw": "🤝 Ничья!",

        "guess_title": "🔢 <b>Угадай число!</b>\nЯ загадал число от 1 до 10.\n\nИспользуй: /guess <число>",
        "guess_usage": "🔢 Введи: /guess <число от 1 до 10>",
        "guess_correct": "🎉 <b>Правильно!</b> Число было {number}!\nПопыток: {attempts}",
        "guess_wrong": "❌ Не угадал! Попробуй <b>{hint}</b>.\nПопыток: {attempts}",
        "guess_higher": "больше",
        "guess_lower": "меньше",

        "trivia_correct": "🎉 <b>Правильно!</b> Отлично!",
        "trivia_wrong": "😢 <b>Неправильно!</b> В следующий раз повезёт!",
        "trivia_usage": "🧠 Введи: /trivia <номер ответа>",
        "trivia_no_active": "🧠 Нет активной викторины. Начни с /trivia",

        # Fun
        "joke_title": "😂 <b>Случайная шутка</b>",
        "fact_title": "🧠 <b>Знаешь ли ты?</b>",
        "roll_title": "🎲 <b>Бросок!</b>\n\nВыпало: <b>{number}</b>",

        # Music
        "music_usage": "🎵 Использование: /music <название>\nПример: /music Imagine Dragons Bones",
        "music_ask_query": "🎵 Введи название песни:",
        "music_searching": "🔍 Ищу: <b>{query}</b>...",
        "music_not_found": "❌ Ничего не найдено по запросу: <b>{query}</b>",
        "music_caption": "🎵 {duration}",
        "music_too_large": "❌ Файл слишком большой для Telegram",

        # Admin
        "admin_panel_title": "⚙️ <b>Панель управления</b>\n\n{statuses}\n\nНажми для переключения:",
        "admin_antispam": "🛡 Анти-спам",
        "admin_moderation": "📝 Модерация",
        "admin_links": "🔗 Фильтр ссылок",
        "admin_media": "📷 Фильтр медиа",
        "admin_nsfw": "🔞 Фильтр 18+",
        "admin_badwords": "🚫 Мат-фильтр",
        "admin_captcha": "🎭 CAPTCHA",
        "admin_raid": "⚠️ Рейд-режим",
        "admin_close": "❌ Закрыть",
        "on": "✅ ВКЛ",
        "off": "❌ ВЫКЛ",

        # Warnings
        "warn_no_reply": "Ответь на сообщение пользователя, чтобы выдать предупреждение.",
        "warn_message": "{user} предупреждён ({count}/3). Причина: {reason}",
        "warn_auto_muted": "{user} автоматически замучен: 3/3 предупреждения.",
        "unwarn_no_reply": "Ответь на сообщение пользователя, чтобы снять предупреждение.",
        "unwarn_no_warnings": "У пользователя нет предупреждений.",
        "unwarn_message": "{user} — предупреждение снято. Осталось: {count}",
        "mute_no_reply": "Ответь на сообщение пользователя, чтобы замутить.",
        "mute_message": "{user} замучен на {duration}. Причина: {reason}",
        "unmute_no_reply": "Ответь на сообщение пользователя, чтобы размутить.",
        "unmute_message": "{user} размучен.",
        "warnings_title": "📋 Предупреждения для {user}:",
        "warnings_empty": "У {user} нет предупреждений.",

        # Leaderboard
        "leaderboard_title": "🏆 <b>Таблица лидеров</b>",
        "leaderboard_empty": "🏆 <b>Таблица лидеров</b>\n\nЕщё никто не играл!",
        "your_stats": "\n📊 <b>Твоя статистика:</b>",
        "stats_title": "📊 <b>Статистика для {name}</b>",
        "stats_empty": "📊 <b>Твоя статистика</b>\n\nТы ещё не играл! Попробуй /rps, /guess или /trivia.",
        "stats_overall": "\n📈 <b>Всего</b>: {total} игр, {win_rate:.0f}% побед",
        "stats_no_games": "Нет сыгранных игр.",

        # Moderation
        "mod_spam": "Спам: {reason}",
        "mod_profanity": "Мат: {word}",
        "mod_links": "Ссылки запрещены",
        "mod_media": "Медиа запрещены",
        "mod_muted": "{user} замучен ({count}/3) — {reason}",
        "mod_warned": "{user}, предупреждение {count}/3: {reason}",

        # Captcha
        "captcha_prompt": "🔐 <b>Добро пожаловать!</b>\n\nЧтобы подтвердить, что ты не бот, введи код с картинки:\n⏳ У тебя 60 секунд",
        "captcha_passed": "✅ <b>{name}</b>, капча пройдена! Добро пожаловать!",
        "captcha_wrong": "❌ Неправильно! Осталось попыток: <b>{attempts}</b>",
        "captcha_too_many": "🚫 {name}, слишком много попыток. Ты заблокирован.",
        "captcha_expired": "⏰ Время на капчу истекло. Ты заблокирован.",

        # Scheduler
        "schedule_ask_text": "📝 Введи текст сообщения (или нажми «Пропустить» если только фото):",
        "schedule_ask_photo": "📷 Пришли фото, видео, GIF, стикер, документ или нажми «Пропустить»:",
        "schedule_ask_photo_again": "📷 Пришли медиа (фото/видео/GIF/документ/голосовое) или нажми «Пропустить»:",
        "schedule_ask_media_again": "📷 Пришли медиа (фото/видео/GIF/документ/голосовое) или нажми «Пропустить»:",
        "schedule_ask_interval": "⏰ Через сколько часов повторять?",
        "schedule_invalid_interval": "❌ Введи число от 1 до 24",
        "schedule_empty": "❌ Текст и фото пустые. Создание отменено.",
        "schedule_created": "✅ Рассылка #{id} создана! Каждые {interval}ч",
        "schedule_none": "📋 Нет активных рассылок.",
        "schedule_list_title": "📋 <b>Рассылки:</b>",
        "schedule_del_usage": "Использование: /schedule_del <id>",
        "schedule_deleted": "✅ Рассылка #{id} удалена.",
        "schedule_not_found": "❌ Рассылка #{id} не найдена.",
        "skip": "Пропустить",

        # WebApp
        "panel_title": "⚙️ <b>Панель управления</b>\n\nНажми кнопку <b>Menu</b> внизу чата, чтобы открыть панель.",
        "panel_button": "⚙️ Открыть панель",
        "panel_not_admin": "❌ Только админы могут управлять настройками.",
        "panel_dm_title": "⚙️ <b>Выбери группу:</b>",
        "panel_no_groups": "❌ Ты не админ ни в одной группе с ботом.",
        "panel_menu_set": "✅ Кнопка <b>Menu</b> установлена! Обнови чат (выйди и зайди снова) и нажми <b>Menu</b> внизу.",

        # Game names
        "game_rps": "🪨 Камень-Ножницы-Бумага",
        "game_guess": "🔢 Угадай число",
        "game_trivia": "🧠 Викторина",
        "game_dice": "🎲 Кубик",

        # Menu
        "menu_games": "🎮 Игры",
        "menu_joke": "😂 Шутка",
        "menu_fact": "🧠 Факт",
        "menu_dice": "🎲 Кубик",
        "menu_stats": "📊 Статистика",
        "menu_help": "❓ Помощь",
        "menu_back": "🔙 Назад",
    },
    "en": {
        # Start / Help
        "start_welcome": (
            "👋 <b>Hello, {name}!</b>\n\n"
            "I'm a multi-purpose bot — I protect chats and entertain you! 🛡️🎮\n\n"
            "<b>Commands:</b>\n\n"
            "🛡️ <b>Protection</b>\n"
            "  /admin — Open admin panel\n"
            "  /warn &lt;reply&gt; [reason] — Warn a user\n"
            "  /mute &lt;reply&gt; [duration] — Mute a user\n"
            "  /unmute &lt;reply&gt; — Unmute a user\n"
            "  /unwarn &lt;reply&gt; — Remove warning\n"
            "  /warnings &lt;reply&gt; — Show user warnings\n\n"
            "🎮 <b>Games</b>\n"
            "  /rps — Rock-Paper-Scissors 🪨📄✂️\n"
            "  /dice — Roll dice 🎲\n"
            "  /dart — Throw dart 🎯\n"
            "  /bowling — Bowling 🎳\n"
            "  /guess — Guess the number 🔢\n"
            "  /trivia — Trivia quiz 🧠\n\n"
            "😂 <b>Fun</b>\n"
            "  /joke — Random joke 😂\n"
            "  /fact — Random fact 🧠\n"
            "  /music — Search music 🎵\n"
            "  /roll — Random number 🎲\n\n"
            "📊 <b>Stats</b>\n"
            "  /top — Leaderboard 🏆\n"
            "  /stats — Your stats\n\n"
            "🌐 /language — Switch language / Сменить язык"
        ),
        "help_title": "❓ <b>Help</b> — press /start",
        "language_prompt": "🌐 <b>Choose language / Выбери язык:</b>",
        "language_set_ru": "✅ Язык установлен: <b>Русский</b>",
        "language_set_en": "✅ Language set: <b>English</b>",

        # Games
        "rps_title": "🪨📄✂️ <b>Rock-Paper-Scissors!</b>\nChoose your move:",
        "rps_usage": "🪨📄✂️ <b>Rock-Paper-Scissors!</b>\n\nUsage: /rps rock|paper|scissors",
        "rps_user": "You",
        "rps_bot": "Bot",
        "rps_win": "🎉 You win!",
        "rps_loss": "😢 Bot wins!",
        "rps_draw": "🤝 Draw!",

        "guess_title": "🔢 <b>Guess the number!</b>\nI'm thinking of 1 to 10.\n\nUse: /guess <number>",
        "guess_usage": "🔢 Enter: /guess <number from 1 to 10>",
        "guess_correct": "🎉 <b>Correct!</b> The number was {number}!\nAttempts: {attempts}",
        "guess_wrong": "❌ Wrong! Try <b>{hint}</b>.\nAttempts: {attempts}",
        "guess_higher": "higher",
        "guess_lower": "lower",

        "trivia_correct": "🎉 <b>Correct!</b> Great job!",
        "trivia_wrong": "😢 <b>Wrong!</b> Better luck next time!",
        "trivia_usage": "🧠 Enter: /trivia <option number>",
        "trivia_no_active": "🧠 No active trivia. Start with /trivia",

        # Fun
        "joke_title": "😂 <b>Random Joke</b>",
        "fact_title": "🧠 <b>Did you know?</b>",
        "roll_title": "🎲 <b>Roll!</b>\n\nYou rolled: <b>{number}</b>",

        # Music
        "music_usage": "🎵 Usage: /music <query>\nExample: /music Imagine Dragons Bones",
        "music_ask_query": "🎵 Enter a song name:",
        "music_searching": "🔍 Searching: <b>{query}</b>...",
        "music_not_found": "❌ Nothing found for: <b>{query}</b>",
        "music_caption": "🎵 {duration}",
        "music_too_large": "❌ File too large for Telegram",

        # Admin
        "admin_panel_title": "⚙️ <b>Панель управления</b>\n\n{statuses}\n\nНажми для переключения:",
        "admin_antispam": "🛡 Анти-спам",
        "admin_moderation": "📝 Модерация",
        "admin_links": "🔗 Фильтр ссылок",
        "admin_media": "📷 Фильтр медиа",
        "admin_nsfw": "🔞 Фильтр 18+",
        "admin_badwords": "🚫 Мат-фильтр",
        "admin_captcha": "🎭 CAPTCHA",
        "admin_raid": "⚠️ Рейд-режим",
        "admin_close": "❌ Закрыть",
        "on": "✅ ВКЛ",
        "off": "❌ ВЫКЛ",

        # Warnings
        "warn_no_reply": "Reply to a user to warn them.",
        "warn_message": "{user} warned ({count}/3). Reason: {reason}",
        "warn_auto_muted": "{user} auto-muted: 3/3 warnings.",
        "unwarn_no_reply": "Reply to a user to unwarn them.",
        "unwarn_no_warnings": "This user has no warnings.",
        "unwarn_message": "{user} unwarned. Warnings: {count}",
        "mute_no_reply": "Reply to a user to mute them.",
        "mute_message": "{user} muted for {duration}. Reason: {reason}",
        "unmute_no_reply": "Reply to a user to unmute them.",
        "unmute_message": "{user} unmuted.",
        "warnings_title": "📋 Warnings for {user}:",
        "warnings_empty": "{user} has no warnings.",

        # Leaderboard
        "leaderboard_title": "🏆 <b>Leaderboard</b>",
        "leaderboard_empty": "🏆 <b>Leaderboard</b>\n\nNo games played yet!",
        "your_stats": "\n📊 <b>Your stats:</b>",
        "stats_title": "📊 <b>Statistics for {name}</b>",
        "stats_empty": "📊 <b>Your Statistics</b>\n\nNo games played yet! Try /rps, /guess or /trivia.",
        "stats_overall": "\n📈 <b>Overall</b>: {total} games, {win_rate:.0f}% win rate",
        "stats_no_games": "No games played yet.",

        # Moderation
        "mod_spam": "Spam: {reason}",
        "mod_profanity": "Profanity: {word}",
        "mod_links": "Links not allowed",
        "mod_media": "Media not allowed",
        "mod_muted": "{user} muted ({count}/3) — {reason}",
        "mod_warned": "{user}, warning {count}/3: {reason}",

        # Captcha
        "captcha_prompt": "🔐 <b>Welcome!</b>\n\nTo prove you're not a bot, enter the code from the image:\n⏳ You have 60 seconds",
        "captcha_passed": "✅ <b>{name}</b>, captcha passed! Welcome!",
        "captcha_wrong": "❌ Wrong! Attempts left: <b>{attempts}</b>",
        "captcha_too_many": "🚫 {name}, too many attempts. You are banned.",
        "captcha_expired": "⏰ Captcha time expired. You are banned.",

        # Scheduler
        "schedule_ask_text": "📝 Enter message text (or press «Skip» if photo only):",
        "schedule_ask_photo": "📷 Send a photo, video, GIF, sticker, document or press «Skip»:",
        "schedule_ask_photo_again": "📷 Send media (photo/video/GIF/document/voice) or press «Skip»:",
        "schedule_ask_media_again": "📷 Send media (photo/video/GIF/document/voice) or press «Skip»:",
        "schedule_ask_interval": "⏰ Repeat every how many hours?",
        "schedule_invalid_interval": "❌ Enter a number from 1 to 24",
        "schedule_empty": "❌ Text and photo are empty. Cancelled.",
        "schedule_created": "✅ Scheduled post #{id} created! Every {interval}h",
        "schedule_none": "📋 No active scheduled posts.",
        "schedule_list_title": "📋 <b>Scheduled posts:</b>",
        "schedule_del_usage": "Usage: /schedule_del <id>",
        "schedule_deleted": "✅ Scheduled post #{id} deleted.",
        "schedule_not_found": "❌ Scheduled post #{id} not found.",
        "skip": "Skip",

        # WebApp
        "panel_title": "⚙️ <b>Admin Panel</b>\n\nPress the <b>Menu</b> button at the bottom of the chat to open the panel.",
        "panel_button": "⚙️ Open panel",
        "panel_not_admin": "❌ Only admins can manage settings.",
        "panel_dm_title": "⚙️ <b>Select a group:</b>",
        "panel_no_groups": "❌ You are not an admin in any group with the bot.",
        "panel_menu_set": "✅ Menu button set! Refresh the chat (leave and rejoin) and press <b>Menu</b> at the bottom.",

        # Game names
        "game_rps": "🪨 Rock-Paper-Scissors",
        "game_guess": "🔢 Guess the Number",
        "game_trivia": "🧠 Trivia",
        "game_dice": "🎲 Dice",

        # Menu
        "menu_games": "🎮 Games",
        "menu_joke": "😂 Joke",
        "menu_fact": "🧠 Fact",
        "menu_dice": "🎲 Dice",
        "menu_stats": "📊 Stats",
        "menu_help": "❓ Help",
        "menu_back": "🔙 Back",
    },
}

# Default language
DEFAULT_LANG = "ru"


def t(key: str, lang: str = DEFAULT_LANG, default: Optional[str] = None, **kwargs) -> str:
    """Translate a key to the given language, formatting with kwargs."""
    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    text = translations.get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, default or key)
    if kwargs:
        text = text.format(**kwargs)
    return text
