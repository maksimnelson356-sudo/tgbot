#!/usr/bin/env python3
"""
webhook_server.py — Простой вебхук-сервер для GitHub.
Слушает POST-запросы от GitHub и вызывает deploy.sh.

Запуск: python3 webhook_server.py
Порт: 9000 (настройте в GitHub webhook)
"""

import hashlib
import hmac
import os
import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройки
PORT = 9000
SECRET = os.environ.get("WEBHOOK_SECRET", "my_secret_token_change_me")
DEPLOY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.sh")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Проверяем подпись GitHub
        signature = self.headers.get("X-Hub-Signature-256", "")
        if SECRET:
            expected = "sha256=" + hmac.new(
                SECRET.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Invalid signature")
                return

        # Проверяем что это push event
        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Pong")
            return

        if event != "push":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Ignored event")
            return

        # Запускаем деплой
        try:
            result = subprocess.run(
                ["bash", DEPLOY_SCRIPT],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout + result.stderr
            status = 200 if result.returncode == 0 else 500
        except Exception as e:
            output = str(e)
            status = 500

        self.send_response(status)
        self.end_headers()
        self.wfile.write(output.encode())

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"Webhook server listening on port {PORT}")
    print(f"Deploy script: {DEPLOY_SCRIPT}")
    print(f"Secret: {'***' if SECRET else 'NONE (open)'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
