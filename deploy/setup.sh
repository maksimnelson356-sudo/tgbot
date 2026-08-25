#!/bin/bash
# setup.sh — первоначальная настройка на VPS
# Запустить один раз: sudo bash setup.sh

set -e

BOT_DIR="/opt/tgbot"
REPO_URL="https://github.com/maksimnelson356-sudo/tgbot.git"
BOT_USER="tgbot"

echo "=== Setting up TG Bot ==="

# Устанавливаем Python и git
echo "Installing dependencies..."
apt update -qq
apt install -y python3 python3-pip python3-venv git

# Создаём непривилегированного пользователя для бота
if ! id "$BOT_USER" &>/dev/null; then
    echo "Creating system user $BOT_USER..."
    useradd --system --shell /usr/sbin/nologin --home-dir "$BOT_DIR" "$BOT_USER"
fi

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

# Права: владелец — tgbot
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
chmod +x deploy/deploy.sh deploy/webhook_server.py

# .env должен существовать и принадлежать tgbot
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "ERROR: $BOT_DIR/.env not found. Create it from .env.example and fill in secrets."
    exit 1
fi
chmod 600 "$BOT_DIR/.env"
chown "$BOT_USER:$BOT_USER" "$BOT_DIR/.env"

# WEBHOOK_SECRET обязателен для вебхук-сервера
if ! grep -q "^WEBHOOK_SECRET=" "$BOT_DIR/.env"; then
    echo "Generating WEBHOOK_SECRET and appending to .env..."
    echo "WEBHOOK_SECRET=$(openssl rand -hex 32)" >> "$BOT_DIR/.env"
fi

# Sudo-правило: tgbot может только перезапускать сервис бота
echo "Installing sudoers rule..."
cat > /etc/sudoers.d/tgbot-restart <<EOF
$BOT_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart tgbot
EOF
chmod 440 /etc/sudoers.d/tgbot-restart

# Копируем systemd сервисы
echo "Installing systemd services..."
cp deploy/tgbot.service /etc/systemd/system/
cp deploy/tgbot-webhook.service /etc/systemd/system/

# Запускаем сервисы
systemctl daemon-reload
systemctl enable tgbot tgbot-webhook
systemctl start tgbot tgbot-webhook

SECRET_VALUE=$(grep "^WEBHOOK_SECRET=" "$BOT_DIR/.env" | cut -d= -f2)

echo ""
echo "=== DONE! ==="
echo ""
echo "Bot service:  systemctl status tgbot"
echo "Webhook:      systemctl status tgbot-webhook"
echo "Logs bot:     journalctl -u tgbot -f"
echo "Logs webhook: journalctl -u tgbot-webhook -f"
echo ""
echo "Next step: Add webhook in GitHub repo:"
echo "  Settings -> Webhooks -> Add webhook"
echo "  Payload URL: http://YOUR_SERVER_IP:9000  (или https через reverse-proxy)"
echo "  Content type: application/json"
echo "  Secret: $SECRET_VALUE"
echo "  Events: Just the push event"
