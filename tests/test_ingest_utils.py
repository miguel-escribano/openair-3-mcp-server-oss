"""Unit tests for CSV/Excel ingest helpers and upload parsing."""
from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openair_mcp.datetime_parse import parse_series_timestamp
from openair_mcp.utils import series_from_csv_text, series_from_excel_bytes


def test_parse_series_timestamp_spain_suffix():
    ts = parse_series_timestamp("23/06/2026 00:00h", source_timezone="Europe/Madrid")
    assert ts.endswith("Z")
    assert "2026-06-22" in ts or "2026-06-23" in ts


def test_series_from_csv_text_spain_fixture():
    fixture = ROOT / "fixtures" / "sample_spain_hourly.csv"
    text = fixture.read_text(encoding="utf-8")
    series = series_from_csv_text(
        text,
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    assert len(series.timestamps) == 5
    assert series.series[0].name == "PM10"


def test_series_from_excel_bytes_roundtrip():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["date", "PM10"])
    ws.append(["23/06/2026 00:00h", 58])
    ws.append(["23/06/2026 01:00h", 55])
    buf = BytesIO()
    wb.save(buf)

    series = series_from_excel_bytes(
        buf.getvalue(),
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    assert len(series.timestamps) == 2
    assert series.series[0].values == [58.0, 55.0]


def test_series_from_csv_text_with_lat_lon():
    fixture = ROOT / "fixtures" / "sample_spain_hourly.csv"
    text = fixture.read_text(encoding="utf-8")
    series = series_from_csv_text(
        text,
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
        site="Felisa Munarriz, Pamplona",
        lat=42.80686,
        lon=-1.64405,
    )
    assert series.meta is not None
    assert series.meta.lat == 42.80686
    assert series.meta.lon == -1.64405


def test_prepare_meta_preserves_lat_lon():
    from openair_mcp.prepare import prepare_series_for_openair

    series = series_from_csv_text(
        ROOT.joinpath("fixtures/sample_spain_hourly.csv").read_text(encoding="utf-8"),
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
        site="Felisa Munarriz, Pamplona",
        lat=42.80686,
        lon=-1.64405,
    )
    prep = prepare_series_for_openair(data=series, granularity="hourly")
    assert prep["meta"]["lat"] == 42.80686
    assert prep["meta"]["lon"] == -1.64405


def test_upload_tool_via_server():
    from server import load_series_from_upload

    fixture = ROOT / "fixtures" / "sample_spain_hourly.csv"
    b64 = base64.b64encode(fixture.read_bytes()).decode("ascii")
    result = load_series_from_upload(
        content_base64=b64,
        file_type="csv",
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    assert "error" not in result
    assert len(result["timestamps"]) == 5


def test_wind_series_from_csv_felisa_fixture():
    from openair_mcp.utils import wind_series_from_csv

    fixture = ROOT / "fixtures" / "felisa_munarriz_wind.csv"
    if not fixture.is_file():
        return  # regenerate with scripts/inject_real_wind.py

    wind = wind_series_from_csv(
        fixture,
        datetime_col="date",
        timezone="UTC",
        site="Felisa Munarriz, Pamplona",
        lat=42.80686,
        lon=-1.64405,
    )
    assert len(wind.timestamps) > 100
    assert len(wind.ws) == len(wind.timestamps)
    assert len(wind.wd) == len(wind.timestamps)
    assert len(wind.series) >= 3
    assert wind.meta is not None
    assert wind.meta.lat == 42.80686
