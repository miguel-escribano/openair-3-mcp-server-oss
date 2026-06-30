"""Convert generic JSON time-series export payloads into SeriesV1 for prepare/plot tools."""
from __future__ import annotations

import re
from typing import Any

from openair_mcp.contracts import SeriesV1


def normalize_param(name: str) -> str:
    return name.lower().replace(".", "").replace("_", "").replace(" ", "")


def export_to_series_v1(
    export: dict[str, Any],
    filter_names: list[str] | None = None,
) -> dict[str, Any] | None:
    """Prefer export.series_v1; fall back to parameters[].data buckets."""
    existing = export.get("series_v1")
    if isinstance(existing, dict) and existing.get("timestamps") and existing.get("series"):
        if not filter_names:
            return existing
        wanted = {normalize_param(n) for n in filter_names}
        series = [
            col
            for col in existing.get("series") or []
            if isinstance(col, dict)
            and normalize_param(str(col.get("name", ""))) in wanted
        ]
        if not series:
            return None
        return {"timestamps": list(existing["timestamps"]), "series": series}

    params = export.get("parameters") or []
    if not params:
        return None

    if filter_names:
        wanted = {normalize_param(n) for n in filter_names}
        params = [
            p
            for p in params
            if isinstance(p, dict)
            and normalize_param(str(p.get("parameter", ""))) in wanted
        ]
        if not params:
            return None

    common_keys: set[str] | None = None
    for param in params:
        keys = set((param.get("data") or {}).keys())
        common_keys = keys if common_keys is None else common_keys & keys
    if not common_keys:
        return None

    keys_sorted = sorted(common_keys)
    timestamps = [k.replace(" ", "T") + ":00Z" for k in keys_sorted]
    series: list[dict[str, Any]] = []
    for param in params:
        buckets = param.get("data") or {}
        values: list[float | None] = []
        for key in keys_sorted:
            bucket = buckets.get(key)
            if isinstance(bucket, dict):
                values.append(bucket.get("mean"))
            else:
                values.append(bucket)
        series.append(
            {
                "name": str(param.get("parameter", "unknown")),
                "unit": str(param.get("unit") or ""),
                "values": values,
            }
        )
    return {"timestamps": timestamps, "series": series}


def _device_label(device: str, pollutant: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", device).strip("_")
    return f"{safe or 'device'}_{pollutant}"


def merge_json_exports(
    exports: list[dict[str, Any]],
    filter_names: list[str] | None = None,
) -> dict[str, Any] | None:
    """Align one pollutant column per export onto a shared timestamp union."""
    pollutant = str((filter_names or ["co2"])[0])
    merged: list[tuple[str, str, dict[str, float | None]]] = []
    all_ts: set[str] = set()

    for export in exports:
        built = export_to_series_v1(export, [pollutant])
        if not built or not built.get("series"):
            return None
        col = built["series"][0]
        device = str(export.get("device") or "device")
        label = _device_label(device, str(col.get("name") or pollutant))
        ts_list = built["timestamps"]
        values = col.get("values") or []
        ts_to_val = dict(zip(ts_list, values))
        all_ts.update(ts_list)
        merged.append((label, str(col.get("unit") or ""), ts_to_val))

    if len(merged) < 2:
        return None

    timestamps_sorted = sorted(all_ts)
    return {
        "timestamps": timestamps_sorted,
        "series": [
            {
                "name": label,
                "unit": unit,
                "values": [mapping.get(ts) for ts in timestamps_sorted],
            }
            for label, unit, mapping in merged
        ],
    }


def series_has_numeric_values(data: dict[str, Any]) -> bool:
    for col in data.get("series") or []:
        if not isinstance(col, dict):
            continue
        if any(v is not None for v in (col.get("values") or [])):
            return True
    return False


def resolve_prepare_input(
    data: SeriesV1 | dict[str, Any] | None,
    json_exports: list[dict[str, Any]] | None,
    series_name: str | None,
    parameter: str | None,
) -> tuple[SeriesV1 | None, str | None, dict[str, Any] | None]:
    """Resolve SeriesV1 from explicit data and/or JSON export payloads."""
    filters: list[str] | None = None
    if series_name:
        filters = [series_name]
    elif parameter:
        filters = [parameter]

    if json_exports:
        if len(json_exports) == 1:
            built = export_to_series_v1(json_exports[0], filters)
            source = "json_export"
        else:
            built = merge_json_exports(json_exports, filters)
            source = "json_exports_merged"
        if not built or not series_has_numeric_values(built):
            return (
                None,
                None,
                {
                    "error": "Could not build numeric series from json_exports.",
                    "data_source": "error",
                    "hint": (
                        "Each payload must include series_v1 or parameters[].data with "
                        "numeric values. For two devices, pass both exports in json_exports "
                        "and set parameter (e.g. no2)."
                    ),
                },
            )
        return SeriesV1.model_validate(built), source, None

    if data is not None:
        model = data if isinstance(data, SeriesV1) else SeriesV1.model_validate(data)
        payload = model.model_dump()
        if not series_has_numeric_values(payload):
            return (
                None,
                None,
                {
                    "error": (
                        "data has structure but no numeric values. "
                        "Pass SeriesV1 with values or use json_exports."
                    ),
                    "data_source": "error",
                    "hint": "Never fabricate null placeholder arrays.",
                },
            )
        return model, "explicit_data", None

    return (
        None,
        None,
        {
            "error": "Provide data (SeriesV1) or json_exports from your data pipeline.",
            "data_source": "error",
        },
    )
