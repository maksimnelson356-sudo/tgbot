import logging

from telethon import TelegramClient

from config import settings

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


async def get_client() -> TelegramClient | None:
    """Get or create the Telethon client. Returns None if not configured."""
    global _client

    if _client is not None and _client.is_connected():
        return _client

    if not settings.TELETHON_API_ID or not settings.TELETHON_API_HASH:
        logger.warning("Telethon not configured (missing TELETHON_API_ID/TELETHON_API_HASH)")
        return None

    try:
        _client = TelegramClient(
            settings.TELETHON_SESSION,
            settings.TELETHON_API_ID,
            settings.TELETHON_API_HASH,
        )
        await _client.start(bot_token=settings.BOT_TOKEN)
        logger.info("Telethon client started")
        return _client
    except Exception as e:
        logger.error("Failed to start Telethon client: %s", e)
        _client = None
        return None


async def stop_client() -> None:
    """Disconnect the Telethon client."""
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
        _client = None
        logger.info("Telethon client stopped")
