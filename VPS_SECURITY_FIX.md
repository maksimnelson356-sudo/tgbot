# 🔐 Security Fix — применено на VPS

> **Контекст:** старый webhook-секрет (`my_secret_token_change_me`) был закоммичен
> в публичный репозиторий. Сервер: бот уже работал от непривилегированного
> пользователя `user` (не root), но вебхук-сервер был не установлен,
> а sudo требует пароль. Ниже — фактически применённая схема БЕЗ root.

## Архитектура после фикса

```
Git push → GitHub webhook → webhook_server.py (:9000, HMAC-SHA256) → deploy.sh → git pull → pkill bot.py → systemd перезапускает tgbot
```

- Вебхук и бот работают от одного непривилегированного пользователя.
- Секрет хранится в `/opt/tgbot/.env` (`WEBHOOK_SECRET`), сервер не стартует без него (min 32 символа).
- Рестарт бота без sudo: deploy.sh завершает процесс — systemd-юнит `tgbot`
  (Restart=always) сам поднимает свежий код через ~10 секунд.
- Автостарт вебхука — через crontab `@reboot`.

## Что было сделано автоматически

1. Сгенерирован новый `WEBHOOK_SECRET` (openssl rand -hex 32), добавлен в `.env`.
2. `.env` → chmod 600.
3. Код задеплоен (git pull), вебхук запущен от `user`, автостарт через cron.
4. deploy.sh переведён на рестарт без sudo.

## Единственный ручной шаг — ротация секрета в GitHub

1. Открой: https://github.com/maksimnelson356-sudo/tgbot/settings/hooks
2. Зайди в существующий webhook (или Create webhook, если его нет):
   - **Payload URL**: `http://2.26.105.72:9000/`
   - **Content type**: `application/json`
   - **Secret**: значение `WEBHOOK_SECRET` из `/opt/tgbot/.env` на сервере
     (посмотреть: `ssh user@2.26.105.72 'grep WEBHOOK_SECRET /opt/tgbot/.env'`)
   - **Events**: Just the push event
3. Save. Должна появиться зелёная галочка (ping = Pong).

## Проверка работы автодеплоя

```bash
git commit --allow-empty -m "test: webhook" && git push origin main
# через ~20 сек:
ssh user@2.26.105.72 'tail -5 /opt/tgbot/deploy/deploy.log'
ssh user@2.26.105.72 'systemctl show tgbot -p ActiveEnterTimestamp'
```

## Остаточные риски (нужен root, применить при возможности)

| Риск | Митигирование сейчас | Фикс с root |
|---|---|---|
| Порт 9000 открыт всему миру | 64-символьный HMAC-секрет, проверка подписи constant-time | ufw: разрешить 9000 только для GitHub IP (`https://api.github.com/meta` → `hooks`), либо reverse-proxy с TLS |
| Юнит tgbot не имеет hardening | работает от user (не root) | drop-in с NoNewPrivileges/PrivateTmp |
| Нет отдельного sudo-правила | рестарт через pkill+Restart=always | `user ALL=(root) NOPASSWD: /usr/bin/systemctl restart tgbot` и возврат к systemctl в deploy.sh |
