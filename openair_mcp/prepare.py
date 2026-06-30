"""Align SeriesV1 onto a deterministic local time grid for openair plotting."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from openair_mcp.contracts import SeriesV1
from openair_mcp.export_bridge import resolve_prepare_input
from openair_mcp.text_encoding import normalize_label
from openair_mcp.time_grid import _raw_minutes, build_expected_buckets, floor_bucket

_CALENDAR_GRANULARITIES = {"hourly", "daily", "weekly", "monthly"}


def _valid_granularity(g: str) -> bool:
    if g in _CALENDAR_GRANULARITIES:
        return True
    n = _raw_minutes(g)
    return n is not None and 0 < n <= 1440
_PREP_GAP_POLICIES = {"preserve", "strict"}


def _resolve_tz(timezone_name: str):
    """UTC without ZoneInfo for Windows hosts missing tzdata."""
    if timezone_name.upper() in ("UTC", "ETC/UTC", "GMT", "Z"):
        return timezone.utc
    return ZoneInfo(timezone_name)


def _parse_iso_to_tz(ts: str, tz) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def prepare_series_for_openair(
    data: SeriesV1 | dict[str, Any] | None = None,
    json_exports: list[dict[str, Any]] | None = None,
    series_name: str | None = None,
    parameter: str | None = None,
    granularity: str = "hourly",
    timezone_name: str = "UTC",
    gap_policy: str = "preserve",
    coverage_threshold: float = 0.9,
    max_points: int = 10000,
) -> dict:
    """Prepare deterministic aligned timestamps/values for OpenAir plotting."""
    resolved, data_source, err = resolve_prepare_input(
        data, json_exports, series_name, parameter
    )
    if err:
        return err
    assert resolved is not None and data_source is not None

    result = _prepare_series_for_openair(
        resolved,
        series_name=series_name,
        granularity=granularity,
        timezone_name=timezone_name,
        gap_policy=gap_policy,
        coverage_threshold=coverage_threshold,
        max_points=max_points,
    )
    if "error" not in result:
        result["data_source"] = data_source
    return result


def _prepare_series_for_openair(
    data: SeriesV1,
    series_name: str | None = None,
    granularity: str = "hourly",
    timezone_name: str = "UTC",
    gap_policy: str = "preserve",
    coverage_threshold: float = 0.9,
    max_points: int = 10000,
) -> dict:
    """Core alignment logic (SeriesV1 input only)."""
    if not _valid_granularity(granularity):
        return {"error": "Invalid granularity. Use hourly, daily, weekly, monthly, or raw_Nm (e.g. raw_5m, raw_15m, raw_30m)."}
    if gap_policy not in _PREP_GAP_POLICIES:
        return {"error": "Invalid gap_policy. Use preserve or strict."}
    if not (0.0 <= coverage_threshold <= 1.0):
        return {"error": "coverage_threshold must be between 0 and 1."}
    if max_points < 10:
        return {"error": "max_points must be >= 10."}

    try:
        tz = _resolve_tz(timezone_name)
    except Exception:
        return {"error": f"Invalid timezone: {timezone_name}"}

    if not data.timestamps:
        return {"error": "timestamps cannot be empty."}

    if series_name:
        want = normalize_label(series_name)
        columns = [col for col in data.series if normalize_label(col.name) == want]
        if not columns:
            return {"error": f"series_name '{series_name}' not found."}
    else:
        columns = list(data.series)

    warnings: list[str] = []
    all_pairs: list[tuple[datetime, float | None]] = []
    for col in columns:
        pair_count = min(len(data.timestamps), len(col.values))
        if pair_count == 0:
            return {"error": f"No overlapping timestamp/value pairs for series '{col.name}'."}
        if len(data.timestamps) != len(col.values):
            warnings.append(
                f"{col.name}: input lengths differ (timestamps={len(data.timestamps)}, "
                f"values={len(col.values)}); using first {pair_count} pairs."
            )
        for i in range(pair_count):
            all_pairs.append((_parse_iso_to_tz(data.timestamps[i], tz), col.values[i]))

    all_pairs.sort(key=lambda x: x[0])
    start_local = floor_bucket(all_pairs[0][0], granularity)
    end_local = floor_bucket(all_pairs[-1][0], granularity)

    expected_buckets, grid_err = build_expected_buckets(
        start_local, end_local, granularity, tz, max_points=max_points
    )
    if grid_err:
        grid_err["timezone"] = timezone_name
        return grid_err

    def _bucket_column(col) -> tuple[list[str], list[float | None], int]:
        pair_count = min(len(data.timestamps), len(col.values))
        pairs: list[tuple[datetime, float | None]] = []
        for i in range(pair_count):
            pairs.append((_parse_iso_to_tz(data.timestamps[i], tz), col.values[i]))
        pairs.sort(key=lambda x: x[0])

        bucket_values: dict[datetime, list[float]] = {}
        for ts_local, value in pairs:
            if value is None:
                continue
            bucket = floor_bucket(ts_local, granularity)
            bucket_values.setdefault(bucket, []).append(float(value))

        timestamps_out: list[str] = []
        values_out: list[float | None] = []
        actual_points = 0
        for bucket in expected_buckets:
            timestamps_out.append(
                bucket.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            vals = bucket_values.get(bucket, [])
            if vals:
                actual_points += 1
                values_out.append(round(sum(vals) / len(vals), 4))
            else:
                values_out.append(None)
        return timestamps_out, values_out, actual_points

    prepared_columns: list[dict] = []
    timestamps: list[str] = []
    primary_actual = 0
    for col in columns:
        ts_out, values_out, actual_points = _bucket_column(col)
        if not timestamps:
            timestamps = ts_out
            primary_actual = actual_points
        prepared_columns.append(
            {
                "name": normalize_label(col.name),
                "unit": normalize_label(col.unit) if col.unit else col.unit,
                "values": values_out,
            }
        )

    expected_points = len(expected_buckets)
    missing_points = expected_points - primary_actual
    coverage_ratio = round(primary_actual / expected_points, 6) if expected_points else 0.0
    primary = columns[0]

    if gap_policy == "strict" and coverage_ratio < coverage_threshold:
        return {
            "error": (
                f"Coverage {coverage_ratio:.3f} below strict threshold "
                f"{coverage_threshold:.3f}."
            ),
            "series_name": primary.name,
            "granularity_effective": granularity,
            "timezone": timezone_name,
            "expected_points": expected_points,
            "actual_points": primary_actual,
            "missing_points": missing_points,
            "coverage_ratio": coverage_ratio,
        }

    if missing_points > 0:
        warnings.append(
            f"{missing_points} missing buckets preserved as null (gap_policy={gap_policy})."
        )
    n = _raw_minutes(granularity)
    if n is not None and n < 60:
        warnings.append(f"{granularity} can produce large payloads for long date ranges.")

    meta_out: dict | None = None
    if data.meta:
        meta_out = data.meta.model_dump(mode="json", exclude_none=True)
    if meta_out is None:
        meta_out = {"source": "file"}
    meta_out["timezone"] = timezone_name

    return {
        "series_name": normalize_label(primary.name),
        "unit": normalize_label(primary.unit) if primary.unit else primary.unit,
        "series_names": [col["name"] for col in prepared_columns],
        "granularity_requested": granularity,
        "granularity_effective": granularity,
        "timezone": timezone_name,
        "gap_policy": gap_policy,
        "expected_points": expected_points,
        "actual_points": primary_actual,
        "missing_points": missing_points,
        "coverage_ratio": coverage_ratio,
        "start_effective": timestamps[0] if timestamps else None,
        "end_effective": timestamps[-1] if timestamps else None,
        "timestamps": timestamps,
        "values": prepared_columns[0]["values"],
        "series": prepared_columns,
        "meta": meta_out,
        "warnings": warnings,
    }
