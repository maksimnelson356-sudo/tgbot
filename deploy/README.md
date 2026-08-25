# Авто-деплой бота

## Как это работает

```
Git push → GitHub вебхук → Webhook сервер (127.0.0.1:9000) → deploy.sh → git pull → sudo systemctl restart tgbot
```

Модель безопасности:
- Вебхук-сервер работает от непривилегированного пользователя `tgbot`.
- Секрет `WEBHOOK_SECRET` хранится только в `/opt/tgbot/.env` (не в гите), сервер не стартует без него.
- Рестарт бота разрешён sudo-правилом только для одной команды (`systemctl restart tgbot`).
- Наружу отдаётся только статус деплоя; полный вывод — в journald.

## Первоначальная настройка на VPS

1. Скопируй репозиторий на VPS и создай `.env` из `.env.example` (заполни токены).
2. Запусти setup:
   ```bash
   sudo bash deploy/setup.sh
   ```
   Скрипт создаст системного пользователя `tgbot`, сгенерирует `WEBHOOK_SECRET`,
   установит systemd-сервисы и sudo-правило.
3. Посмотри сгенерированный секрет:
   ```bash
   grep WEBHOOK_SECRET /opt/tgbot/.env
   ```
4. Настрой GitHub webhook:
   - Репозиторий → Settings → Webhooks → Add webhook
   - Payload URL: `http://ТВОЙ_IP:9000` (лучше https через reverse-proxy)
   - Content type: `application/json`
   - Secret: значение из `/opt/tgbot/.env`
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

# Лог деплоя
tail -f /opt/tgbot/deploy/deploy.log

# Ручной деплой (без вебхука)
cd /opt/tgbot && bash deploy/deploy.sh
```

## Порт 9000

По умолчанию сервер слушает `127.0.0.1:9000` — снаружи недоступен.

Варианты проброса наружу (по убыванию безопасности):
1. **Reverse-proxy с TLS** (nginx + Let's Encrypt) → в GitHub указывай https-URL.
2. **Файрвол по IP GitHub**: разреши порт 9000 только для [GitHub webhook IP-адресов](https://api.github.com/meta) (`hooks`), затем запусти сервис с `WEBHOOK_BIND=0.0.0.0` (через drop-in override).

Открывать `9000` всему миру без TLS/фильтрации — нельзя.
