# Telegram Bot Project Presentation

## Overview
This is a multifunctional Telegram bot designed for group moderation and entertainment. It combines anti-spam protection, content moderation, admin management, games, music, AI chat, reputation systems, and social features like marriages and birthdays.

## Key Features

### Protection & Moderation
- Automatic spam, profanity, NSFW, link, media, forward, and contact filtering
- Homoglyph detection to catch obfuscated profanity
- AI moderation (Google Gemini) for text and image analysis
- Customizable CAPTCHA for new members
- Raid mode detection (multiple joins in short time)
- Warning system with auto-mute after 3 warnings

### Administration
- Dual admin system: Telegram admins + bot-assigned ranks (1-3)
- `/admin` command for inline keyboard controls (rank 3+)
- `/panel` command for WebApp-based admin interface (Mini App)
- Bot-admins can use moderation commands without Telegram admin rights

### Entertainment & Games
- Rock-Paper-Scissors (`/rps`)
- Number guessing (`/guess`)
- Trivia quizzes (`/trivia`)
- Dice games (`/dice`, `/dart`, `/bowling`)
- Hug animations (`/hug`)
- Jokes and facts (`/joke`, `/fact`)
- Random number rolls (`/roll`)

### Music
- `/music` command to search and download tracks from Hitmo
- Inline keyboard interface with pagination
- 30-second audio previews
- Deduplication and caching system

### Social Features
- Marriage system: `/marry` (proposal), `/unmarry` (divorce), `/marriage` (status)
- Gift system: `/gift` to send reputation to spouse
- Birthday tracking: `/setbday`, `/birthdays`
- Family leaderboard: `/familytop`

### Utilities
- Notes system (`/note`, `/notes`, `/delnote`)
- Auto-replies (`/addreply`, `/listreplies`, `/delreply`)
- Chat rules (`/setrules`, `/rules`, `/delrules`)
- Slow mode, pin/unpin, whitelist links
- Log channel (`/setlog`, `/remlog`)
- Sticker bans (`/bansticker`, `/unbansticker`)
- Day statistics (`/daystats`)
- Find zombie/ghost accounts (`/zombies`)

### Technical Stack
- **Framework**: aiogram 3.x (async Python Telegram bot)
- **Database**: SQLite via SQLAlchemy 2.0 + aiosqlite
- **AI**: Google Gemini 2.0 Flash (text & vision)
- **Music**: Hitmo service (HTML scraping)
- **Captcha**: Pillow library (image generation)
- **Deployment**: systemd service + GitHub webhook (port 9000)
- **Admin Panel**: Static HTML hosted on GitHub Pages

## Configuration (.env)
```
BOT_TOKEN=your_telegram_bot_token
GOOGLE_API_KEY=your_google_ai_studio_key
OWNER_ID=your_telegram_id_for_feedback
TELETHON_API_ID=your_telethon_api_id
TELETHON_API_HASH=your_telethon_api_hash
TELETHON_SESSION=tgbot_userbot
DATABASE_URL=sqlite+aiosqlite:///data/tgbot.db
LOG_LEVEL=INFO
```

## Deployment
1. VPS with Debian 12, Python 3.11+
2. Systemd services: `tgbot` (bot) and `tgbot-webhook` (port 9000)
3. Auto-deploy: GitHub push → webhook → deploy.sh → git pull → pip install → systemctl restart tgbot
4. Admin Panel: https://maksimnelson356-sudo.github.io/tgbot/static/admin_panel.html

## Bot Admin Permissions Required
To function fully, the bot needs administrator rights with:
- Delete messages
- Ban/restrict users
- Pin messages
- Invite users (for CAPTCHA)
- Change info (if needed)

## Command Reference
See `COMMANDS.md` for complete command list with descriptions and required permissions.