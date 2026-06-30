"""Tests for DST-safe bucket grids and prepare_series alignment."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openair_mcp.contracts import SeriesColumnV1, SeriesMetaV1, SeriesV1
from openair_mcp.prepare import _prepare_series_for_openair
from openair_mcp.time_grid import _raw_minutes, build_expected_buckets, utc_timestamps_unique


def test_raw_minutes_helper():
    assert _raw_minutes("raw_5m") == 5
    assert _raw_minutes("raw_15m") == 15
    assert _raw_minutes("raw_30m") == 30
    assert _raw_minutes("hourly") is None
    assert _raw_minutes("raw_xm") is None


def test_raw_5m_buckets_one_hour():
    """raw_5m should produce 12 buckets per hour, no duplicates."""
    tz = ZoneInfo("UTC")
    start = datetime(2024, 1, 1, 0, 0, tzinfo=tz)
    end = datetime(2024, 1, 1, 0, 55, tzinfo=tz)
    buckets, err = build_expected_buckets(start, end, "raw_5m", tz, max_points=1000)
    assert err is None
    assert len(buckets) == 12
    assert utc_timestamps_unique(buckets)


def test_raw_30m_buckets_one_day():
    """raw_30m should produce 48 buckets per day."""
    tz = ZoneInfo("UTC")
    start = datetime(2024, 1, 1, 0, 0, tzinfo=tz)
    end = datetime(2024, 1, 1, 23, 30, tzinfo=tz)
    buckets, err = build_expected_buckets(start, end, "raw_30m", tz, max_points=1000)
    assert err is None
    assert len(buckets) == 48
    assert utc_timestamps_unique(buckets)


def test_budapest_spring_dst_no_duplicate_utc():
    tz = ZoneInfo("Europe/Budapest")
    start = datetime(2026, 3, 17, 0, 0, tzinfo=tz)
    end = datetime(2026, 4, 19, 23, 0, tzinfo=tz)
    buckets, err = build_expected_buckets(start, end, "hourly", tz, max_points=10000)
    assert err is None
    assert len(buckets) == 815
    assert utc_timestamps_unique(buckets)


def test_prepare_aligns_timestamps_and_values_with_gaps():
    tz = ZoneInfo("Europe/Budapest")
    start = datetime(2026, 3, 17, 0, 0, tzinfo=tz)
    end = datetime(2026, 4, 19, 23, 0, tzinfo=tz)
    cur = start
    ts: list[str] = []
    vals: list[float | None] = []
    i = 0
    while cur <= end:
        ts.append(cur.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        vals.append(None if i in (100, 200, 300, 400, 500, 600) else 800.0 + (i % 50))
        cur += timedelta(hours=1)
        i += 1

    data = SeriesV1(
        timestamps=ts,
        series=[SeriesColumnV1(name="co2", unit="ppm", values=vals)],
        meta=SeriesMetaV1(source="other", timezone="Europe/Budapest"),
    )
    prep = _prepare_series_for_openair(
        data,
        granularity="hourly",
        timezone_name="Europe/Budapest",
        gap_policy="preserve",
    )
    assert "error" not in prep
    assert len(prep["timestamps"]) == len(prep["values"]) == prep["expected_points"]
    assert prep["expected_points"] == 815
    assert prep["missing_points"] >= 6
    assert len(prep["timestamps"]) == len(set(prep["timestamps"]))
