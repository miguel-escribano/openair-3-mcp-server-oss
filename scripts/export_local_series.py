#!/usr/bin/env python3
"""Export a local CSV or Excel file to SeriesV1 JSON (same parser as load_series_from_*).

For agent-capable harnesses (Cursor, VS Code, Claude Code, Codex): the agent runs this
script — it does not parse the file in chat. No R required; only Python + openpyxl for xlsx.

  pip install -e .   # from openair-3-mcp-server-oss repo root
  python scripts/export_local_series.py --input data.xlsx --datetime-col "Fecha/hora" \\
    --columns PM10 --timezone Europe/Madrid --site "Felisa Munarriz" \\
    --lat 42.80686 --lon -1.64405 --output _series_v1.json

Then: prepare_series_for_openair(data=<json>) on the openair MCP server → plot.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openair_mcp.utils import series_from_csv, series_from_excel  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Export local CSV/xlsx to SeriesV1 JSON")
    p.add_argument("--input", required=True, help="Path to CSV or .xlsx on the local machine")
    p.add_argument("--datetime-col", default="date", help="Datetime column header")
    p.add_argument(
        "--columns",
        nargs="*",
        default=None,
        help="Pollutant column name(s); omit to use all non-datetime columns",
    )
    p.add_argument("--timezone", default="UTC", help="IANA zone for naive timestamps")
    p.add_argument("--site", default=None, help="Optional site label")
    p.add_argument("--lat", type=float, default=None, help="Optional station latitude (WGS84)")
    p.add_argument("--lon", type=float, default=None, help="Optional station longitude (WGS84)")
    p.add_argument(
        "--dedupe-timestamps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep last row when duplicate hours appear",
    )
    p.add_argument(
        "--output",
        default="_series_v1.json",
        help="Write SeriesV1 JSON here (default: _series_v1.json)",
    )
    p.add_argument(
        "--sheet",
        default=None,
        help="Excel worksheet name (default: active sheet)",
    )
    args = p.parse_args()

    path = Path(args.input)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        series = series_from_csv(
            path,
            datetime_col=args.datetime_col,
            columns=args.columns,
            timezone=args.timezone,
            site=args.site,
            lat=args.lat,
            lon=args.lon,
            dedupe_timestamps=args.dedupe_timestamps,
        )
    elif suffix in (".xlsx", ".xlsm"):
        series = series_from_excel(
            path,
            sheet_name=args.sheet,
            datetime_col=args.datetime_col,
            columns=args.columns,
            timezone=args.timezone,
            site=args.site,
            lat=args.lat,
            lon=args.lon,
            dedupe_timestamps=args.dedupe_timestamps,
        )
    else:
        print(f"Unsupported extension {suffix!r}; use .csv or .xlsx", file=sys.stderr)
        return 1

    out = Path(args.output)
    out.write_text(
        json.dumps(series.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(series.timestamps)} timestamps, {len(series.series)} series -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
