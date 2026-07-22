# TG Bot — Шпаргалка для продолжения работы

## Команда для быстрого входа
Скажи: **"tgbot"** — и я сразу вспомню весь проект.

## Быстрые ссылки
- **Локально**: D:\Scripts\tgbot
- **VPS**: /opt/tgbot (2.26.105.72, Debian 12, Python 3.11)
- **GitHub**: https://github.com/maksimnelson356-sudo/tgbot.git
- **Mini App**: https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html

## Деплой
```
git push origin main
```
На VPS: `cd /opt/tgbot && git pull origin main && systemctl restart tgbot`

## Systemd
- `systemctl restart tgbot` — бот
- `systemctl restart tgbot-webhook` — вебхук (порт 9000)
- `journalctl -u tgbot -f` — логи

## .env (VPS)
```
BOT_TOKEN=...
GOOGLE_API_KEY=AIza...   ← ключ Google AI Studio (не AQ.)
OWNER_ID=<telegram_id>   ← для /feedback, узнать через @userinfobot
```

## Ключевые файлы
- `bot.py` — точка входа, порядок роутеров
- `config.py` — настройки (pydantic-settings, .env), OWNER_ID
- `handlers/protection/admin_panel.py` — панель админа (Inlinekbd, /panel)
- `handlers/protection/warnings.py` — Пред/Мут/Бан + /warn /mute /ban
- `handlers/protection/captcha_handler.py` — капча для новых участников
- `handlers/protection/autoresponder.py` — авто-ответы по ключевым словам
- `handlers/protection/antispam.py` — рейды, спам, NSFW
- `handlers/protection/ai_chat.py` — Gemini AI (text + photo moderation)
- `handlers/protection/webapp.py` — Mini App панель + toggle настроек
- `handlers/entertainment/games.py` — /rps /guess /trivia
- `handlers/entertainment/music.py` — поиск и воспроизведение музыки (Hitmo)
- `handlers/entertainment/fun.py` — /dice /flip /coin /8ball
- `handlers/language.py` — /language ru|en
- `handlers/feedback.py` — /feedback → OWNER_ID
- `handlers/info.py` — /start /help /rules /id /me
- `handlers/scheduler.py` — отложенные посты
- `services/music_service.py` — Hitmo HTML-парсер, кэш
- `services/ai_moderation.py` — Gemini text + photo moderation
- `services/captcha.py` — генерация капчи
- `utils/i18n.py` — переводы (ru/en)
- `utils/helpers.py` — delete_after, schedule_delete, format_time
- `filters/admin.py` — HasRank(min_rank), IsAdmin
- `filters/chat_type.py` — IsGroup, IsPrivate, IsReplyToBot, HasPendingCaptcha, HasMatchingAutoReply
- `db/models.py` — ChatAdmin с rank 1/2/3, Chat, User, ScheduledPost
- `db/queries.py` — все запросы к БД
- `db/base.py` — async_session_factory, init_db
- `static/admin_panel.html` — HTML-панель для Mini App
- `deploy/` — скрипты деплоя

## Порядок роутеров (КРИТИЧНО!)
moderation_router перехватывает ВЕСЬ текст в группах (`~F.text.startswith("/")`)!
Поэтому он ДОЛЖЕН быть ПОСЛЕДНИМ роутером.

Порядок в bot.py:
1. start — /start, приветствие
2. music_router — FSM для /music
3. ai_chat_router — ответы на реплаи к боту (IsReplyToBot)
4. captcha_router — ответы на капчу (HasPendingCaptcha)
5. admin_panel — панель админа, /panel
6. warnings — Пред/Мут/Бан
7. games — /rps /guess /trivia
8. fun — /dice /flip /coin /8ball
9. leaderboard, info, language, report, purge, notes, reputation, bansticker, rules, zombies
10. autoresponder_router — авто-ответы (HasMatchingAutoReply)
11. slowmode_cmd, stats_daily, birthdays, weather, feedback, setlog, utilities, scheduler, webapp
12. antispam_handler — рейды, новые участники
13. moderation_router — ПОСЛЕДНИЙ, перехватывает остаток текста

## Фильтры (важные)
- **IsReplyToBot** — реплаи на сообщения бота (ai_chat)
- **HasPendingCaptcha** — пользователь с непройденной капчей
- **HasMatchingAutoReply** — текст совпадает с авто-ответом
- **IsGroup / IsPrivate** — тип чата
- **IsAdmin / HasRank(n)** — проверка прав

## Ранги
1 = 🔰 Младший (Пред, Мут)
2 = 🛡️ Администратор (+ Бан)
3 = 👑 Главный (+ Назначение админов, /admin)

## Текстовые команды
Повысить (reply) → +1 ранг | Понизить → снять админа
Пред (reply) → варн | Мут (reply) → мут 1ч | Бан (reply) → бан

## Важные замечания
- `F.reply_to_message` **не работает** в этой версии aiogram — используется кастомный `IsReplyToBot`
- `InputFile` **абстрактный** в aiogram 3 — использовать `BufferedInputFile` (BytesIO) или `FSInputFile` (файлы)
- `bot.__call__` auto-delete **убран** — было слишком агрессивно (удаляло ВСЕ сообщения бота). Используй `_delete_later` в хендлерах.
- `setChatMenuButton` **не работает** в группах (ограничение Telegram API)
- `WebApp` кнопки **запрещены** в группах (BUTTON_TYPE_INVALID)
- Капча **выключена** из панели админа и Mini App
- Ключи в `.env`: `AIza...` (Google AI Studio), НЕ `AQ.` (устаревший)
- Кэш музыки: ключи по 8 символов, TTL 30 минут
