"""DST-safe local time bucket grids for prepare_series_for_openair."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _raw_minutes(granularity: str) -> int | None:
    """Return N for 'raw_Nm' strings (e.g. raw_5m -> 5), or None otherwise."""
    if granularity.startswith("raw_") and granularity.endswith("m"):
        try:
            return int(granularity[4:-1])
        except ValueError:
            return None
    return None


def floor_bucket(dt: datetime, granularity: str) -> datetime:
    n = _raw_minutes(granularity)
    if n is not None:
        minute = (dt.minute // n) * n
        return dt.replace(minute=minute, second=0, microsecond=0)
    if granularity == "hourly":
        return dt.replace(minute=0, second=0, microsecond=0)
    if granularity == "daily":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "weekly":
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start - timedelta(days=day_start.weekday())
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _utc_step(granularity: str) -> timedelta:
    n = _raw_minutes(granularity)
    if n is not None:
        return timedelta(minutes=n)
    return timedelta(hours=1)


def _floor_bucket_utc(dt: datetime, granularity: str) -> datetime:
    dt = dt.astimezone(timezone.utc)
    n = _raw_minutes(granularity)
    if n is not None:
        minute = (dt.minute // n) * n
        return dt.replace(minute=minute, second=0, microsecond=0)
    return dt.replace(minute=0, second=0, microsecond=0)


def build_expected_buckets(
    start_local: datetime,
    end_local: datetime,
    granularity: str,
    tz: ZoneInfo,
    *,
    max_points: int,
) -> tuple[list[datetime], dict | None]:
    """Collect ordered local bucket starts from start_local to end_local (inclusive).

    Walks the UTC timeline and floors each instant to a local bucket key so
    non-existent DST hours (e.g. 02:00 on spring-forward day) are never emitted.
    """
    start_local = floor_bucket(start_local, granularity)
    end_local = floor_bucket(end_local, granularity)
    step = _utc_step(granularity)
    pad = step * 48

    start_utc = start_local.astimezone(timezone.utc) - pad
    end_utc = end_local.astimezone(timezone.utc) + pad

    seen: dict[str, datetime] = {}
    cur_utc = _floor_bucket_utc(start_utc, granularity)
    end_walk = end_utc + pad

    while cur_utc <= end_walk:
        bucket = floor_bucket(cur_utc.astimezone(tz), granularity)
        if start_local <= bucket <= end_local:
            seen[bucket.isoformat()] = bucket
            if len(seen) > max_points:
                return [], {
                    "error": (
                        f"Expected points exceed max_points ({max_points}). "
                        "Reduce date range or use coarser granularity."
                    ),
                    "granularity": granularity,
                }
        cur_utc += step

    buckets = sorted(seen.values(), key=lambda b: b.astimezone(timezone.utc))
    return buckets, None


def utc_timestamps_unique(buckets: list[datetime]) -> bool:
    """True when each bucket maps to a distinct UTC ISO Z string."""
    seen: set[str] = set()
    for bucket in buckets:
        key = bucket.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if key in seen:
            return False
        seen.add(key)
    return True
