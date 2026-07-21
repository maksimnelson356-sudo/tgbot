#!/bin/bash
# deploy.sh — скрипт обновления бота
# Вызывается вебхуком при пуше в репозиторий

BOT_DIR="/root/tgbot"
LOG_FILE="/var/log/tgbot-deploy.log"

echo "=== Deploy started: $(date) ===" >> "$LOG_FILE"

cd "$BOT_DIR" || { echo "DIR NOT FOUND: $BOT_DIR" >> "$LOG_FILE"; exit 1; }

# Сохраняем текущий коммит
OLD_COMMIT=$(git rev-parse HEAD)

# Pulllatest
git pull origin main 2>> "$LOG_FILE"
NEW_COMMIT=$(git rev-parse HEAD)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo "No changes, skipping restart." >> "$LOG_FILE"
    exit 0
fi

echo "Updated: $OLD_COMMIT -> $NEW_COMMIT" >> "$LOG_FILE"

# Устанавливаем зависимости (если изменились)
if git diff "$OLD_COMMIT" "$NEW_COMMIT" --name-only | grep -q "requirements.txt"; then
    echo "Installing requirements..." >> "$LOG_FILE"
    source venv/bin/activate
    pip install -r requirements.txt -q >> "$LOG_FILE"
fi

# Перезапускаем бота
if systemctl is-active --quiet tgbot; then
    systemctl restart tgbot
    echo "Bot restarted via systemd." >> "$LOG_FILE"
else
    # Если нет systemd — убиваем старый процесс и запускаем новый
    pkill -f "python bot.py" 2>/dev/null
    sleep 2
    source venv/bin/activate
    nohup python bot.py >> /var/log/tgbot.log 2>&1 &
    echo "Bot restarted via nohup. PID: $!" >> "$LOG_FILE"
fi

echo "=== Deploy finished: $(date) ===" >> "$LOG_FILE"
