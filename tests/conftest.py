"""Shared test fixtures for tgbot test suite."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_bot():
    """Mock aiogram Bot instance."""
    bot = AsyncMock()
    bot.get_me.return_value = MagicMock(id=123456, username="test_bot")
    bot.send_message = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.get_file = AsyncMock()
    bot.download_file = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Mock aiogram Message for testing handlers."""
    msg = MagicMock()
    msg.from_user = MagicMock(id=111, username="testuser", first_name="Test", is_bot=False)
    msg.chat = MagicMock(id=-100123, type="group", title="Test Group")
    msg.text = "test message"
    msg.caption = None
    msg.message_id = 100
    msg.answer = AsyncMock()
    msg.delete = AsyncMock()
    msg.bot = MagicMock()
    return msg


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_settings():
    """Mock bot settings."""
    return {
        "moderation_enabled": True,
        "bad_words_enabled": True,
        "nsfw_filter_enabled": True,
        "filter_links": False,
        "filter_media": False,
        "antiforward_enabled": False,
        "antispam_contacts": False,
        "max_warnings": 3,
        "mute_duration": 900,
        "allowed_domains": [],
    }
