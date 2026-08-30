"""Timezone helpers.

The bot may run on a VPS in UTC while its audience lives in another zone.
All "daily reset" boundaries (rep quota, /daily streak, birthdays, weekly
digest, retention jobs) must use the configured local timezone instead of
bare ``datetime.now()`` / ``date.today()``.

DB columns store naive ``datetime`` (SQLite DateTime). To stay comparable,
we produce naive UTC values everywhere: ``now_utc_naive()`` for "now" and
``start_of_day_utc_naive()`` for "local midnight as UTC-naive".
"""

import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from config import settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def now_utc_naive() -> datetime.datetime:
    """Current moment as a naive UTC datetime (matches DB stored values)."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def now_local() -> datetime.datetime:
    """Current moment as a timezone-aware datetime in the local zone."""
    return datetime.datetime.now(local_tz())


def today_local() -> datetime.date:
    """Local calendar date (for birthday/digest/weekday decisions)."""
    return now_local().date()


def start_of_day_utc_naive() -> datetime.datetime:
    """Midnight of the current local day, converted to naive UTC.

    Example (VPS UTC, zone Europe/Moscow): at 01:30 MSK this returns
    the UTC-naive datetime of the previous 21:00 UTC — the moment the
    local day started.
    """
    local_midnight = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def start_of_local_day_for(dt: Optional[datetime.datetime]) -> datetime.date:
    """Local-date portion of a naive datetime, interpreted as UTC.

    Falls back to today's local date when the value is missing.
    """
    if dt is None:
        return today_local()
    return dt.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz()).date()