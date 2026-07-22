from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///tgbot.db"
    LOG_LEVEL: str = "INFO"

    # Throttling defaults
    THROTTLE_MESSAGES: int = 10
    THROTTLE_WINDOW: int = 5  # seconds
    THROTTLE_BURST: int = 30
    THROTTLE_BURST_WINDOW: int = 30  # seconds

    # CAPTCHA defaults
    CAPTCHA_TIMEOUT: int = 60  # seconds
    CAPTCHA_MAX_ATTEMPTS: int = 3
    CAPTCHA_IMAGE_WIDTH: int = 200
    CAPTCHA_IMAGE_HEIGHT: int = 80
    CAPTCHA_FONT_SIZE: int = 40

    # Raid defaults
    RAID_JOIN_THRESHOLD: int = 5  # users
    RAID_WINDOW: int = 30  # seconds

    # Warning defaults
    WARNINGS_LIMIT: int = 3
    MUTE_DURATION: int = 900  # 15 minutes in seconds

    # Bot info
    BOT_USERNAME: str = ""
    BOT_LANGUAGE: str = "ru"


settings = Settings()  # type: ignore[call-arg]
