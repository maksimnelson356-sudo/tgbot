# Авто-деплой бота

## Как это работает

```
Git push → GitHub вебхук → Webhook сервер (порт 9000) → deploy.sh → git pull → restart bot
```

## Первоначальная настройка на VPS

1. Скопируй файлы на VPS:
   - `deploy/deploy.sh`
   - `deploy/webhook_server.py`
   - `deploy/setup.sh`
   - `deploy/tgbot.service`
   - `deploy/tgbot-webhook.service`

2. Запусти setup:
   ```bash
   # Отредактируй REPO_URL в setup.sh
   nano deploy/setup.sh
   bash deploy/setup.sh
   ```

3. Настрой GitHub webhook:
   - Репозиторий → Settings → Webhooks → Add webhook
   - Payload URL: `http://ТВОЙ_IP:9000`
   - Content type: `application/json`
   - Secret: `my_secret_token_change_me`
   - Events: `Just the push event`

## Полезные команды

```bash
# Статус бота
systemctl status tgbot

# Перезапуск бота
systemctl restart tgbot

# Логи бота
journalctl -u tgbot -f

# Логи вебхука
journalctl -u tgbot-webhook -f

# Ручной деплой (без вебхука)
cd /opt/tgbot && bash deploy/deploy.sh
```

## Структура

```
/root/tgbot/
├── bot.py
├── deploy/
│   ├── deploy.sh           # Скрипт деплоя
│   ├── webhook_server.py   # Вебхук-сервер
│   ├── setup.sh            # Первичная настройка
│   ├── tgbot.service       # Systemd для бота
│   └── tgbot-webhook.service  # Systemd для вебхука
├── handlers/
├── ...
└── requirements.txt
```

## Порт 9000

Открой порт в файрволе:
```bash
ufw allow 9000
# или
iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
```
