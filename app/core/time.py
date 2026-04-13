from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_timezone(timezone_name: str) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def business_date(value: datetime, timezone_name: str) -> date:
    return ensure_utc(value).astimezone(get_timezone(timezone_name)).date()


def date_window_utc(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    tz = get_timezone(timezone_name)
    local_start = datetime.combine(target_date, time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)
