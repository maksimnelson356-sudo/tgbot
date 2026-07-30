# tgbot

Мультифункциональный Telegram-бот на **aiogram 3** с модерацией, играми, музыкой и AI.

## Возможности
- **Модерация**: предупреждения, муты, баны, антиспам, капча, рейд-защита
- **AI-модерация**: Google Gemini (текст + фото)
- **Игры**: камень-ножницы-бумага, угадай число, викторина, кубики
- **Музыка**: поиск через Hitmo, отправка треков
- **Семья/браки**: предложения, разводы, репутация, подарки
- **Админка**: inline-панель + WebApp
- **Автоудаление**: ответы бота в группах удаляются через 15 сек (кроме медиа)

## Быстрые ссылки
- **VPS**: /opt/tgbot (2.26.105.72, Debian 12, Python 3.11)
- **GitHub**: https://github.com/maksimnelson356-sudo/tgbot.git
- **Mini App**: https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html

## Деплой
```
git push origin main
```
На VPS: `cd /opt/tgbot && git pull origin main && systemctl restart tgbot`

## .env
```env
BOT_TOKEN=...
GOOGLE_API_KEY=...      # для AI-модерации и AI-чата
OWNER_ID=123456789      # для /feedback
TELETHON_API_ID=...     # для /zombies
TELETHON_API_HASH=...
```

## Структура проекта
```
bot.py                  # Точка входа, monkey-patch автоудаления
config.py               # Настройки (pydantic-settings)
handlers/               # Хендлеры (protection, entertainment, relationships)
services/               # Сервисы (AI, музыка, капча, спам-детектор)
middlewares/            # Throttling, логирование, автоудаление команд
db/                     # SQLAlchemy модели и запросы
utils/                  # i18n (ru/en), вспомогательные функции
filters/                # Кастомные фильтры (админы, тип чата)
static/admin_panel.html # WebApp панель админа
deploy/                 # Скрипты деплоя, systemd
```
