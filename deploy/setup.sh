#!/bin/bash
# setup.sh — первоначальная настройка на VPS
# Запустить один раз: bash setup.sh

set -e

BOT_DIR="/root/tgbot"
REPO_URL="https://github.com/maksimnelson356-sudo/tgbot.git"

echo "=== Setting up TG Bot ==="

# Устанавливаем Python и git
echo "Installing dependencies..."
apt update -qq
apt install -y python3 python3-pip python3-venv git

# Клонируем репозиторий
if [ ! -d "$BOT_DIR" ]; then
    echo "Cloning repository..."
    if [ -z "$REPO_URL" ]; then
        echo "ERROR: Set REPO_URL in this script!"
        exit 1
    fi
    git clone "$REPO_URL" "$BOT_DIR"
else
    echo "Directory $BOT_DIR already exists, pulling latest..."
    cd "$BOT_DIR"
    git pull
fi

cd "$BOT_DIR"

# Создаём venv и ставим зависимости
echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Копируем systemd сервисы
echo "Installing systemd services..."
cp deploy/tgbot.service /etc/systemd/system/
cp deploy/tgbot-webhook.service /etc/systemd/system/

# Делаем скрипты исполняемыми
chmod +x deploy/deploy.sh
chmod +x deploy/webhook_server.py

# Запускаем сервисы
systemctl daemon-reload
systemctl enable tgbot tgbot-webhook
systemctl start tgbot tgbot-webhook

echo ""
echo "=== DONE! ==="
echo ""
echo "Bot service:  systemctl status tgbot"
echo "Webhook:      systemctl status tgbot-webhook"
echo "Logs bot:     journalctl -u tgbot -f"
echo "Logs webhook: journalctl -u tgbot-webhook -f"
echo ""
echo "Webhook URL: http://YOUR_SERVER_IP:9000"
echo ""
echo "Next step: Add webhook in GitHub repo:"
echo "  Settings -> Webhooks -> Add webhook"
echo "  Payload URL: http://YOUR_SERVER_IP:9000"
echo "  Content type: application/json"
echo "  Secret: my_secret_token_change_me"
echo "  Events: Just the push event"
