# 🤖 BosskoBro Bot — Полная инструкция по настройке и запуску

## Содержание
1. [Что нужно перед началом](#1-что-нужно-перед-началом)
2. [Настройка Telegram бота](#2-настройка-telegram-бота)
3. [Подготовка VPS сервера](#3-подготовка-vps-сервера)
4. [Клонирование и настройка бота](#4-клонирование-и-настройка-бота)
5. [Запуск бота](#5-запуск-бота)
6. [Добавление AI (Gemini)](#6-добавление-ai-gemini)
7. [Настройка GitHub Pages (Mini App)](#7-настройка-github-pages-mini-app)
8. [Полезные команды](#8-полезные-команды)
9. [Решение проблем](#9-решение-проблем)

---

## 1. Что нужно перед началом

| Что | Где взять |
|-----|-----------|
| Telegram аккаунт | Уже есть |
| VPS сервер (Debian 11+) | xorek.cloud или другой хостинг |
| SSH-доступ к серверу | Пароль от root |
| GitHub аккаунт | https://github.com |
| Google API ключ (для AI) | https://aistudio.google.com/app/apikey |

---

## 2. Настройка Telegram бота

### Шаг 2.1: Создай бота через BotFather

1. Открой Telegram, найди **@BotFather**
2. Напиши ему: `/newbot`
3. Он спросит имя — напиши любое, например: `BosskoBro Bot`
4. Он спросит username — напиши уникальный, например: `BosskoBroBot` (должен заканчиваться на `bot`)
5. BotFather пришлёт тебе **токен** — это длинная строка вида `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

**⚠️ СОХРАНИ ТОКЕН! Он нужен для настройки. Никому его не показывай!**

### Шаг 2.2: Настрой бота

В BotFather напиши:
```
/setuserpic
```
и загрузи аватарку для бота.

---

## 3. Подготовка VPS сервера

### Шаг 3.1: Подключись к серверу

Открой терминал (PowerShell / Terminal) и подключись:
```bash
ssh root@2.26.105.72
```
Введи пароль от root.

### Шаг 3.2: Обнови систему
```bash
apt update && apt upgrade -y
```

### Шаг 3.3: Установи Python 3.9 и нужные пакеты
```bash
apt install -y python3 python3-pip python3-venv git ffmpeg
```

### Шаг 3.4: Проверь что всё установилось
```bash
python3 --version
git --version
```
Должны вывести версии. Если нет — что-то пошло не так, напиши мне.

### Шаг 3.5: Настрой firewall (ufw)
```bash
apt install -y ufw
ufw allow 22/tcp
ufw allow 43369/udp
ufw enable
ufw status
```
Должно показать:
```
22/tcp        ALLOW       Anywhere
43369/udp     ALLOW       Anywhere
```

### Шаг 3.6: Установи fail2ban (защита от взлома)
```bash
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 4. Клонирование и настройка бота

### Шаг 4.1: Клонируй репозиторий
```bash
cd /opt
git clone https://github.com/maksimnelson356-sudo/tgbot.git
cd tgbot
```

### Шаг 4.2: Создай виртуальное окружение
```bash
python3 -m venv venv
source venv/bin/activate
```

### Шаг 4.3: Установи зависимости
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 4.4: Создай папку для базы данных
```bash
mkdir -p data
```

### Шаг 4.5: Создай файл .env
```bash
nano .env
```

Вставь следующее (замени `ТВОЙ_ТОКЕН` на токен от BotFather):
```
BOT_TOKEN=ТВОЙ_ТОКЕН
DATABASE_URL=sqlite+aiosqlite:///data/tgbot.db
LOG_LEVEL=INFO
GOOGLE_API_KEY=
```

Нажми `Ctrl+O`, затем `Enter` (сохранить), затем `Ctrl+X` (выйти).

### Шаг 4.6: Сделай первый запуск (чтобы создалась база данных)
```bash
cd /opt/tgbot
source venv/bin/activate
python3 -c "
import asyncio
from db.base import init_db
asyncio.run(init_db())
print('База данных создана!')
"
```

### Шаг 4.7: Проверь что база создалась
```bash
ls -la data/
```
Должен появиться файл `tgbot.db`.

---

## 5. Запуск бота

### Шаг 5.1: Создай systemd-сервис (автозапуск)

```bash
nano /etc/systemd/system/tgbot.service
```

Вставь:
```ini
[Unit]
Description=TG Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tgbot
ExecStart=/opt/tgbot/venv/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Нажми `Ctrl+O` → `Enter` → `Ctrl+X`.

### Шаг 5.2: Запусти бота
```bash
systemctl daemon-reload
systemctl enable tgbot
systemctl start tgbot
```

### Шаг 5.3: Проверь что бот работает
```bash
systemctl status tgbot
```
Должно показать `Active: active (running)` зелёным цветом.

### Шаг 5.4: Посмотри логи
```bash
journalctl -u tgbot -f
```
Нажми `Ctrl+C` чтобы выйти из логов.

Если видишь `Bot started: @UsernameBot (id: 123456)` — бот работает! 🎉

---

## 6. Добавление AI (Gemini)

### Шаг 6.1: Получи API ключ

1. Зайди на https://aistudio.google.com/app/apikey
2. Войди под своим Google-аккаунтом
3. Нажми **"Create API Key"**
4. Скопируй ключ ( длинная строка типа `AIzaSy...` )

### Шаг 6.2: Добавь ключ в .env

```bash
cd /opt/tgbot
nano .env
```

Добавь строку:
```
GOOGLE_API_KEY=AIzaSyТВОЙ_КЛЮЧ
```

Сохрани: `Ctrl+O` → `Enter` → `Ctrl+X`.

### Шаг 6.3: Перезапусти бота
```bash
systemctl restart tgbot
```

---

## 7. Настройка GitHub Pages (Mini App)

### Шаг 7.1: Зайди на GitHub

1. Открой https://github.com/maksimnelson356-sudo/tgbot
2. Нажми **Settings** (вкладка вверху)
3. Слева выбери **Pages**
4. В разделе **Source** выбери: Branch = `main`, Folder = `/ (root)`
5. Нажми **Save**

### Шаг 7.2: Проверь что работает

Подожди 1-2 минуты, затем открой в браузере:
```
https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html
```

Должна открыться красивая панель с переключателями.

---

## 8. Полезные команды

### Управление ботом на сервере

| Команда | Что делает |
|---------|-----------|
| `systemctl status tgbot` | Статус бота (работает/нет) |
| `systemctl restart tgbot` | Перезапуск бота |
| `systemctl stop tgbot` | Остановить бота |
| `systemctl start tgbot` | Запустить бота |
| `journalctl -u tgbot -f` | Смотреть логи в реальном времени |
| `journalctl -u tgbot -n 50` | Последние 50 строк логов |

### Обновление бота (когда в GitHub появились новые изменения)

```bash
cd /opt/tgbot
git pull origin main
systemctl restart tgbot
```

### Команды бота в Telegram

| Команда | Где | Что делает |
|---------|-----|-----------|
| `/start` | Личка | Запуск бота |
| `/help` | Личка | Список команд |
| `/panel` | Личка | Панель управления (через Mini App) |
| `/panel` | Группа | Установить кнопку Menu для панели |
| `/admin` | Группа | Панель настроек (inline-кнопки) |
| `/schedule` | Группа | Создать запланированное сообщение |
| `/schedule_list` | Группа | Список запланированных сообщений |
| `/schedule_del 1` | Группа | Удалить запланированное сообщение |
| `/warn` | Группа | Выдать предупреждение |
| `/ban` | Группа | Забанить пользователя |
| `/mute` | Группа | Заглушить пользователя |
| `/music` | Личка | Поиск музыки на YouTube |
| `/top` | Личка/Группа | Таблица лидеров |

---

## 9. Решение проблем

### Бот не запускается

Посмотри логи:
```bash
journalctl -u tgbot -n 30 --no-pager
```

**Частые ошибки:**

- `ModuleNotFoundError: No module named 'xxx'` — не установлены зависимости:
  ```bash
  cd /opt/tgbot
  source venv/bin/activate
  pip install -r requirements.txt
  systemctl restart tgbot
  ```

- `sqlite3.OperationalError: no such table` — база не создана:
  ```bash
  cd /opt/tgbot
  source venv/bin/activate
  python3 -c "
import asyncio
from db.base import init_db
asyncio.run(init_db())
print('Готово!')
"
  systemctl restart tgbot
  ```

- `Bad Request: BUTTON_TYPE_INVALID` — это было исправлено, обнови код:
  ```bash
  cd /opt/tgbot && git pull origin main && systemctl restart tgbot
  ```

### Бот отвечает в личке, но не в группе

1. Добавь бота в группу
2. Сделай бота **администратором** группы
3. Напиши `/panel` в группе
4. Выйди из группы и зайди снова
5. Внизу чата появится кнопка **Menu**

### AI модерация не работает

Проверь что ключ установлен:
```bash
cat /opt/tgbot/.env
```
Должна быть строка `GOOGLE_API_KEY=AIzaSy...`

### Mini App (панель) не открывается

1. Проверь GitHub Pages: открой в браузере `https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html`
2. Если 404 — подожди ещё минуту, GitHub Pages может задерживаться
3. Если не помогло — зайди в Settings → Pages и убедись что выбран branch `main`

### Бот перестал отвечать

```bash
systemctl status tgbot
```
Если `Active: inactive (dead)` — перезапусти:
```bash
systemctl restart tgbot
```

Если падает сразу после запуска — смотри логи:
```bash
journalctl -u tgbot -n 20 --no-pager
```

---

## 📁 Структура проекта

```
/opt/tgbot/
├── bot.py                  # Точка входа
├── config.py               # Настройки
├── .env                    # Секреты (токен, ключи)
├── requirements.txt        # Зависимости Python
├── data/
│   └── tgbot.db           # База данных
├── db/
│   ├── base.py            # Подключение к БД
│   ├── models.py          # Модели таблиц
│   └── queries.py         # Запросы к БД
├── handlers/
│   ├── start.py           # /start
│   ├── feedback.py        # Обратная связь
│   ├── entertainment/
│   │   ├── fun.py         # Шутки, факты, мемы
│   │   ├── games.py       # Игры (камень-ножницы-бумага)
│   │   ├── leaderboard.py # Таблица лидеров
│   │   ├── music.py       # Поиск музыки
│   │   └── weather.py     # Погода
│   └── protection/
│       ├── admin_panel.py # /admin панель
│       ├── antispam.py    # Анти-спам, рейды
│       ├── captcha_handler.py # CAPTCHA
│       ├── moderation.py  # Модерация, NSFW
│       ├── scheduler.py   # Запланированные сообщения
│       ├── webapp.py      # Mini App обработчик
│       └── warnings.py    # Предупреждения
├── services/
│   ├── ai_moderation.py   # AI-модерация (Gemini)
│   ├── captcha.py         # Генерация CAPTCHA
│   ├── music_service.py   # YouTube поиск
│   ├── scheduler_service.py # Фоновый планировщик
│   ├── spam_detector.py   # Детектор спама
│   └── content_filter.py  # Фильтр контента
├── middlewares/
│   ├── auto_delete.py     # Автоудаление команд
│   ├── logging.py         # Логирование
│   ├── slowmode.py        # Медленный режим
│   └── throttling.py      # Ограничение частоты
├── filters/
│   ├── admin.py           # Фильтры админов
│   └── chat_type.py       # Тип чата
├── utils/
│   ├── i18n.py            # Переводы (RU/EN)
│   └── lang_helper.py     # Определение языка
└── static/
    └── admin_panel.html   # HTML Mini App
```

---

*Инструкция создана 22.07.2026*
