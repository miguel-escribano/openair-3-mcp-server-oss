"""Parse timestamp strings from CSV/Excel exports (ISO, EU day-first, Spanish network quirks)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_PARSE_FORMATS = (
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
)


def _resolve_tz(timezone_name: str):
    if timezone_name.upper() in ("UTC", "ETC/UTC", "GMT", "Z"):
        return timezone.utc
    return ZoneInfo(timezone_name)


def parse_series_timestamp(raw: str, source_timezone: str = "UTC") -> str:
    """Parse one cell value and return a UTC ISO-8601 ``…Z`` string."""
    s = str(raw).strip()
    if not s:
        raise ValueError("empty timestamp")
    s = re.sub(r"h$", "", s, flags=re.IGNORECASE).strip()

    dt: datetime | None = None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        for fmt in _PARSE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        raise ValueError(f"Unrecognized timestamp: {raw!r}")

    tz = _resolve_tz(source_timezone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
