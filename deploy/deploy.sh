#!/bin/bash
# deploy.sh — скрипт обновления бота (вызывается вебхуком при пуше).
# Работает от непривилегированного пользователя-владельца /opt/tgbot БЕЗ sudo.
#
# Рестарт: процесс бота запущен под systemd-юнитом tgbot (Restart=always),
# поэтому просто завершаем его — systemd сам поднимет свежий код через 10с.

BOT_DIR="/opt/tgbot"
LOG_FILE="$BOT_DIR/deploy/deploy.log"

# Защита от параллельных деплоев
exec 9>"$BOT_DIR/deploy/.deploy.lock"
flock -n 9 || { echo "$(date) Deploy already running, skipping" >> "$LOG_FILE"; exit 0; }

echo "=== Deploy started: $(date) ===" >> "$LOG_FILE"

cd "$BOT_DIR" || { echo "DIR NOT FOUND: $BOT_DIR" >> "$LOG_FILE"; exit 1; }

OLD_COMMIT=$(git rev-parse HEAD)

git pull origin main 2>> "$LOG_FILE" || { echo "GIT PULL FAILED" >> "$LOG_FILE"; exit 1; }
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo "No changes, skipping restart." >> "$LOG_FILE"
    exit 0
fi

echo "Updated: $OLD_COMMIT -> $NEW_COMMIT" >> "$LOG_FILE"

# Зависимости — только если менялся requirements.txt
if git diff "$OLD_COMMIT" "$NEW_COMMIT" --name-only | grep -q "requirements.txt"; then
    echo "Installing requirements..." >> "$LOG_FILE"
    source venv/bin/activate
    pip install -r requirements.txt -q >> "$LOG_FILE" 2>&1
fi

# Рестарт без sudo: убиваем процесс — systemd перезапустит юнит tgbot
pkill -f '/opt/tgbot/bot\.py' && {
    echo "Bot process terminated; systemd will restart it with new code." >> "$LOG_FILE"
} || echo "WARNING: bot process not found (not running?)" >> "$LOG_FILE"

echo "=== Deploy finished: $(date) ===" >> "$LOG_FILE"
