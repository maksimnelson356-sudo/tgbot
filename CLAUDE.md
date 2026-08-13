# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-purpose Telegram bot built with **aiogram 3** (async). Handles chat moderation, games, music, family/marriage system, and AI-powered features. Runs on VPS (2.26.105.72) via systemd + webhook auto-deploy.

## Running the Bot

```bash
# Local development
python bot.py

# VPS
cd /opt/tgbot && source venv/bin/activate && python bot.py
```

## Dependencies

```bash
pip install -r requirements.txt
```

Key packages: aiogram 3.18+, SQLAlchemy 2.0 (async), aiosqlite, pydantic-settings, Pillow, beautifulsoup4, telethon, yt-dlp

## Architecture

### Entry Point & Critical Router Order (`bot.py`)

The bot uses aiogram's `Dispatcher` with multiple routers. **Router registration order is critical** — `moderation_router` MUST be last because it catches all remaining group text:

1. `start_router` — /start, welcome
2. `music_router` — FSM for /music
3. `ai_chat_router` — replies to bot messages (uses `IsReplyToBot` filter)
4. `captcha_router` — pending captcha responses (uses `HasPendingCaptcha` filter)
5. `admin_panel_router` through `webapp_router` — various features
6. `antispam_router` — raids, new members
7. `moderation_router` — **LAST** — catches all remaining group text

`bot.py` also applies a monkey-patch to `Message.answer`/`Message.reply` for auto-deleting bot messages in groups after 15 seconds (media excluded).

### Module Structure

- `handlers/` — Message handlers organized by feature
  - `protection/` — Moderation, antispam, captcha, admin panel, warnings, notes, scheduling
  - `entertainment/` — Games, fun commands, music, leaderboard, weather
- `services/` — Business logic (AI moderation via Google Gemini, music search via Hitmo, captcha generation, spam detection, scheduler)
- `middlewares/` — Throttling (token-bucket rate limiter), logging, auto-delete commands, slowmode
- `db/` — SQLAlchemy async models + queries (SQLite via aiosqlite)
  - `models.py` — User, Chat, ChatMember, Warning, ChatAdmin, Marriage, ScheduledPost, etc.
  - `queries.py` — All database queries
  - `base.py` — Async engine, session factory, `init_db()`
- `filters/` — Custom aiogram filters
  - `chat_type.py` — `IsGroup`, `IsPrivate`, `IsReplyToBot`, `HasPendingCaptcha`
  - `admin.py` — `IsAdmin`, `HasRank(min_rank)` (checks Telegram admin + bot-level admin in DB)
- `utils/` — i18n (ru/en translations via `t()` helper), helpers (`delete_after`, `schedule_delete`)
- `keyboards/` — Inline keyboard builders
- `static/admin_panel.html` — WebApp admin panel (Mini App)

### Configuration (`config.py`)

Uses `pydantic-settings` with `.env` file. Key settings:
- `BOT_TOKEN`, `OWNER_ID` (for /feedback)
- `GOOGLE_API_KEY` (AI moderation/chat via Google Gemini)
- `TELETHON_API_ID`/`TELETHON_API_HASH` (member scanning, /zombies)
- Throttling, captcha, raid, and warning limits (all configurable)

### Admin Rank System

Bot-level admins (stored in `ChatAdmin` table) have ranks:
- Rank 1: Junior (warn, mute)
- Rank 2: Administrator (+ ban)
- Rank 3: Head (+ assign admins, /admin)

Telegram native admins bypass rank checks. Check with `HasRank(min_rank)` filter or `get_chat_admin_rank()` query.

### i18n

Translations in `utils/i18n.py`. Use `t("key", lang, **kwargs)` for all user-facing text. Default language is "ru". User language stored in `User.language`.

## Deployment

```bash
# Push triggers webhook auto-deploy
git push origin main

# Manual VPS deploy
cd /opt/tgbot && git pull origin main && systemctl restart tgbot
```

Systemd services: `tgbot` (main bot), `tgbot-webhook` (port 9000)

## Database

SQLite at `data/tgbot.db`. Tables auto-created on startup via `init_db()`. Models use SQLAlchemy 2.0 async mapped columns.

## Known Issues

- `F.reply_to_message` doesn't work in this aiogram version — use `IsReplyToBot` filter
- `InputFile` is abstract in aiogram 3 — use `BufferedInputFile` (BytesIO) or `FSInputFile` (files)
- `setChatMenuButton` doesn't work in groups (Telegram API limitation)
- WebApp buttons are forbidden in groups (BUTTON_TYPE_INVALID)
- Captcha is disabled from admin panel and Mini App
