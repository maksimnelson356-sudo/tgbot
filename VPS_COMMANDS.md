# VPS — Команды для управления ботом

## Деплой (после git push)
```bash
cd /opt/tgbot && git pull origin main && systemctl restart tgbot
```

## Бот
```bash
systemctl restart tgbot          # Перезапустить бота
systemctl status tgbot           # Статус бота
systemctl stop tgbot             # Остановить бота
journalctl -u tgbot -f           # Логи бота (в реальном времени)
journalctl -u tgbot -n 50        # Последние 50 строк логов
```

## Вебхук (автодеплой)
```bash
systemctl restart tgbot-webhook  # Перезапустить вебхук
systemctl status tgbot-webhook   # Статус вебхука
journalctl -u tgbot-webhook -f   # Логи вебхука
```

## Git (обновление)
```bash
cd /opt/tgbot
git pull origin main             # Скачать обновления
systemctl restart tgbot          # Применить
```

## Ручной запуск (без systemd)
```bash
cd /opt/tgbot
source venv/bin/activate
python bot.py                    # Запустить вручную (Ctrl+C для остановки)
```

## Зависимости
```bash
cd /opt/tgbot
source venv/bin/activate
pip install -r requirements.txt  # Установить/обновить зависимости
```

## .env (проверка)
```bash
cat /opt/tgbot/.env              # Посмотреть переменные
```

Нужно:
- `BOT_TOKEN=...`
- `GOOGLE_API_KEY=AIza... или AQ....`   ← ключ Google AI Studio
- `OWNER_ID=<telegram_id>`   ← для /feedback

## База данных
```bash
ls -la /opt/tgbot/data/tgbot.db # Проверить existence БД
sqlite3 /opt/tgbot/data/tgbot.db ".tables"  # Таблицы
```

## Файрвол
```bash
iptables -A INPUT -p tcp --dport 9000 -j ACCEPT  # Открыть порт вебхука
```

## Полезное
```bash
htop                             # Мониторинг процессов
df -h                            # Место на диске
free -m                          # Оперативная память
```
