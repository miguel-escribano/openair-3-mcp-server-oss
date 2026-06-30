"""Synthetic payloads for manifest-driven R script smoke tests."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

_SLOW_TOOLS = frozenset({"polar_cluster", "traj_cluster"})
_TRAJ_MAP_TOOLS = frozenset({"traj_level", "traj_plot"})
_FILE_IMPORT_TOOLS = frozenset({"import_adms", "import_aurn_csv"})
_TWO_SERIES = frozenset({"scatter_plot", "conditional_quantile", "cor_plot"})
_THREE_SERIES = frozenset({"taylor_diagram"})
_TWO_WIND_SERIES = frozenset({"polar_diff"})


def _hourly_timestamps(n: int, start: datetime | None = None) -> list[str]:
    base = start or datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [(base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(n)]


def _series_column(name: str, unit: str, n: int, base: float, step: float) -> dict:
    return {
        "name": name,
        "unit": unit,
        "values": [round(base + i * step, 4) for i in range(n)],
    }


def _deterministic_unit(i: int, salt: int) -> float:
    """Reproducible pseudo-random value in [0, 1) — no RNG, stable across runs."""
    x = (i * 2654435761 + salt * 2246822519) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    return (x & 0xFFFFFF) / 0x1000000


def _wind_grid(n: int) -> tuple[list[float], list[float]]:
    """Non-degenerate, well-spread deterministic wind field for surface-fit tools.

    polarDiff fits a smoothed polar surface per period and subtracts them. A
    periodic/low-cardinality wind field (e.g. wd cycling through 24 fixed
    bearings) collapses the polar grid into duplicate (u, v) cells, so openair's
    pivot_wider yields list-columns and ``after - before`` raises "non-numeric
    argument to binary operator". A scattered wind field keeps each grid cell
    uniquely identified.
    """
    ws = [round(0.5 + _deterministic_unit(i, 1) * 13.5, 3) for i in range(n)]
    wd = [round(_deterministic_unit(i, 2) * 360.0, 2) for i in range(n)]
    return ws, wd


def should_skip_tool(tool_name: str) -> str | None:
    if tool_name in _SLOW_TOOLS and os.getenv("OPENAIR_SMOKE_SLOW", "").strip() not in (
        "1",
        "true",
        "yes",
    ):
        return "slow tool — set OPENAIR_SMOKE_SLOW=1 to include"
    if tool_name in _TRAJ_MAP_TOOLS:
        from openair_mcp.r_bridge import r_package_installed

        for pkg in ("sf", "rnaturalearth"):
            ok, msg = r_package_installed(pkg)
            if not ok:
                return f"{pkg} not installed — traj map tools skipped ({msg})"
    if tool_name in _FILE_IMPORT_TOOLS:
        return (
            "file-import tool — needs an ADMS / AURN-CSV file on the server host; "
            "smoke-skipped (exercise manually with a real file)"
        )
    return None


def build_dst_gap_payload() -> dict:
    """Prepared hourly CO2 with Budapest spring DST + null gaps (regression fixture)."""
    from zoneinfo import ZoneInfo

    from openair_mcp.contracts import SeriesColumnV1, SeriesMetaV1, SeriesV1
    from openair_mcp.prepare import prepare_series_for_openair

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
    prep = prepare_series_for_openair(
        data,
        granularity="hourly",
        timezone_name="Europe/Budapest",
        gap_policy="preserve",
    )
    if prep.get("error"):
        raise RuntimeError(prep["error"])
    n = len(prep["timestamps"])
    if n != len(prep["series"][0]["values"]):
        raise RuntimeError("prepare output timestamps/values length mismatch")
    if len(set(prep["timestamps"])) != n:
        raise RuntimeError("duplicate UTC timestamps in prepared grid")
    return {
        "timestamps": prep["timestamps"],
        "series": prep["series"],
        "meta": {"timezone": "Europe/Budapest", "source": "smoke"},
    }


def build_payload(tool_name: str, manifest: dict) -> dict | None:
    input_type = manifest.get("input_type", "series")
    output_type = manifest.get("output_type", "image")

    if input_type == "import_params":
        if os.getenv("OPENAIR_SMOKE_NETWORK", "").strip() not in ("1", "true", "yes"):
            return None
        return {
            "site": "MY1",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "pollutants": ["no2"],
            "network": "aurn",
            "resolution": "hour",
        }

    if input_type == "traj_series":
        n = 48
        base = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        dates = [(base - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ") for h in range(n)]
        return {
            "date": dates,
            "lat": [51.5 + (i % 10) * 0.01 for i in range(n)],
            "lon": [-0.1 - (i % 10) * 0.01 for i in range(n)],
            "height": [500.0] * n,
            "pressure": [950.0] * n,
            "hour_inc": list(range(-(n - 1), 1)),
        }

    if input_type == "wind_series":
        n = 720 if tool_name in _TWO_WIND_SERIES else 72
        timestamps = _hourly_timestamps(n)
        if tool_name in _TWO_WIND_SERIES:
            # polarDiff subtracts two fitted polar surfaces; it needs a
            # non-degenerate wind field (see _wind_grid).
            ws, wd = _wind_grid(n)
            series = [
                _series_column("NO2_period_a", "µg/m³", n, 12.0, 0.05),
                _series_column("NO2_period_b", "µg/m³", n, 18.0, 0.04),
            ]
        else:
            ws = [2.0 + (i % 12) * 0.3 for i in range(n)]
            wd = [float((i * 15) % 360) for i in range(n)]
            series = [_series_column("NO2", "µg/m³", n, 15.0, 0.08)]
        return {"timestamps": timestamps, "series": series, "ws": ws, "wd": wd}

    # series input_type
    n = 720 if output_type == "stats" else 48
    if tool_name == "theil_sen":
        n = 24 * 30 * 12
    timestamps = _hourly_timestamps(n)
    if tool_name in _THREE_SERIES:
        series = [
            _series_column("obs", "µg/m³", n, 20.0, 0.02),
            _series_column("model_a", "µg/m³", n, 19.0, 0.025),
            _series_column("model_b", "µg/m³", n, 21.0, 0.018),
        ]
    elif tool_name in _TWO_SERIES:
        series = [
            _series_column("CO2", "ppm", n, 420.0, 0.4),
            _series_column("PM25", "µg/m³", n, 12.0, 0.05),
        ]
    else:
        series = [_series_column("CO2", "ppm", n, 400.0, 0.5)]

    payload: dict = {"timestamps": timestamps, "series": series}
    if tool_name == "time_variation":
        payload["meta"] = {"timezone": "Europe/Madrid", "source": "smoke"}
    return payload
