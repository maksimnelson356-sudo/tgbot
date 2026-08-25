#!/usr/bin/env python3
"""
webhook_server.py — Вебхук-сервер для GitHub auto-deploy.
Слушает POST-запросы от GitHub и вызывает deploy.sh.

Требования безопасности:
- WEBHOOK_SECRET обязателен (сервер не стартует без него).
- По умолчанию слушает только 127.0.0.1.
  Для доступа снаружи используйте reverse-proxy с TLS (nginx/caddy)
  либо задайте WEBHOOK_BIND=0.0.0.0 и ограничьте порт файрволом.
"""

import hashlib
import hmac
import os
import subprocess
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler


def _load_env_file(path: str) -> None:
    """Minimal .env loader so cron/@reboot starts work without systemd env."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


# Load secrets from the repo's .env unless already present in the environment
_load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))
BIND_HOST = os.environ.get("WEBHOOK_BIND", "127.0.0.1")
SECRET = os.environ.get("WEBHOOK_SECRET") or ""
DEPLOY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.sh")

if not SECRET:
    sys.exit("FATAL: WEBHOOK_SECRET is not set. Refusing to start.")
if len(SECRET) < 32:
    sys.exit("FATAL: WEBHOOK_SECRET is too short (min 32 chars). Generate: openssl rand -hex 32")

MAX_BODY = 25 * 1024 * 1024  # GitHub payload limit


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_BODY:
            self._reply(413, b"Payload too large")
            return
        body = self.rfile.read(content_length)

        # Проверяем подпись GitHub (HMAC-SHA256)
        signature = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            self._reply(403, b"Invalid signature")
            return

        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self._reply(200, b"Pong")
            return
        if event != "push":
            self._reply(200, b"Ignored event")
            return

        # Запускаем деплой. Наружу отдаём только статус,
        # полный вывод уходит в journald/stderr этого сервиса.
        try:
            result = subprocess.run(
                ["bash", DEPLOY_SCRIPT],
                capture_output=True, text=True, timeout=120,
            )
            print(f"[deploy] rc={result.returncode}\n{result.stdout}{result.stderr}", flush=True)
            status = 200 if result.returncode == 0 else 500
            self._reply(status, b"Deployed" if status == 200 else b"Deploy failed")
        except Exception as e:
            print(f"[deploy] error: {e}", flush=True)
            self._reply(500, b"Deploy error")

    def _reply(self, code: int, payload: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}", flush=True)


def main():
    server = ThreadingHTTPServer((BIND_HOST, PORT), WebhookHandler)
    print(f"Webhook server listening on {BIND_HOST}:{PORT}")
    print(f"Deploy script: {DEPLOY_SCRIPT}")
    print(f"Secret: *** ({len(SECRET)} chars)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
