# TG Bot — Шпаргалка для продолжения работы

## Команда для быстрого входа
Скажи: **"tgbot"** — и я сразу вспомню весь проект.

## Быстрые ссылки
- **Локально**: D:\Scripts\tgbot
- **VPS**: /opt/tgbot (2.26.105.72)
- **GitHub**: https://github.com/maksimnelson356-sudo/tgbot.git

## Деплой
```
git push origin main
```
На VPS: `cd /opt/tgbot && git pull origin main && systemctl restart tgbot`

## Systemd
- `systemctl restart tgbot` — бот
- `systemctl restart tgbot-webhook` — вебхук (порт 9000)
- `journalctl -u tgbot -f` — логи

## Ключевые файлы
- `bot.py` — точка входа, порядок роутеров
- `config.py` — настройки (pydantic-settings, .env)
- `handlers/protection/admin_panel.py` — панель админа + Повысить/Понизить
- `handlers/protection/warnings.py` — Пред/Мут/Бан + /warn /mute /ban
- `handlers/entertainment/games.py` — /rps /guess /trivia (без inline-кнопок)
- `handlers/language.py` — /language ru|en
- `utils/i18n.py` — переводы (ru/en)
- `filters/admin.py` — HasRank(min_rank), IsAdmin
- `db/models.py` — ChatAdmin с rank 1/2/3
- `deploy/` — скрипты деплоя

## Порядок роутеров (КРИТИЧНО!)
moderation_router перехватывает ВЕСЬ текст в группах (~F.text.startswith("/"))!
Поэтому он ДОЛЖЕН быть ПОСЛЕДНИМ роутером.

Порядок в bot.py:
1. music_router — FSM-состояние для /music
2. ai_chat_router — ответы на реплаи к боту
3. captcha_router — ответы на капчу
4. admin_panel, warnings, games, fun, и т.д. — команды
5. autoresponder_router — авто-ответы (текст)
6. antispam_handler — ловит рейды, новые участники
7. moderation_router — ПОСЛЕДНИЙ, перехватывает остаток текста

## Ранги
1 = 🔰 Младший (Пред, Мут)
2 = 🛡️ Администратор (+ Бан)
3 = 👑 Главный (+ Назначение админов, /admin)

## Текстовые команды
Повысить (reply) → +1 ранг | Понизить → снять админа
Пред (reply) → варн | Мут (reply) → мут 1ч | Бан (reply) → бан
