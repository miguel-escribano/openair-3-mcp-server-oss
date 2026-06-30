"""Tests for prepare_series_for_openair meta propagation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openair_mcp.contracts import SeriesColumnV1, SeriesMetaV1, SeriesV1
from openair_mcp.prepare import prepare_series_for_openair


def _felisa_series() -> SeriesV1:
    return SeriesV1(
        timestamps=[
            "2024-01-01T00:00:00Z",
            "2024-01-01T01:00:00Z",
            "2024-01-01T02:00:00Z",
        ],
        series=[SeriesColumnV1(name="PM10", unit="µg/m³", values=[10.0, 12.0, 11.0])],
        meta=SeriesMetaV1(source="file", site="Felisa Munarriz", timezone="Europe/Madrid"),
    )


def test_prepare_preserves_meta_site():
    prep = prepare_series_for_openair(data=_felisa_series(), granularity="hourly")
    assert "error" not in prep
    assert prep["meta"]["site"] == "Felisa Munarriz"
    assert prep["meta"]["source"] == "file"
    assert prep["meta"]["timezone"] == "UTC"


def test_prepare_meta_timezone_from_timezone_name():
    prep = prepare_series_for_openair(
        data=_felisa_series(),
        granularity="hourly",
        timezone_name="Europe/Madrid",
    )
    assert prep["meta"]["timezone"] == "Europe/Madrid"
    assert prep["meta"]["site"] == "Felisa Munarriz"


def test_prepare_meta_when_input_has_no_meta():
    bare = SeriesV1(
        timestamps=["2024-01-01T00:00:00Z"],
        series=[SeriesColumnV1(name="PM10", unit="µg/m³", values=[5.0])],
    )
    prep = prepare_series_for_openair(data=bare, granularity="hourly")
    assert prep["meta"]["source"] == "file"
    assert prep["meta"]["timezone"] == "UTC"


def test_prepare_from_dict_export_path():
    export = _felisa_series().model_dump(mode="json")
    prep = prepare_series_for_openair(data=export, series_name="PM10", granularity="hourly")
    assert prep["meta"]["site"] == "Felisa Munarriz"


def test_prepare_raw_5m_accepted():
    """raw_5m should pass validation and produce sub-hourly buckets."""
    from openair_mcp.contracts import SeriesColumnV1, SeriesV1

    data = SeriesV1(
        timestamps=[
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:05:00Z",
            "2024-01-01T00:10:00Z",
        ],
        series=[SeriesColumnV1(name="CO2", unit="ppm", values=[420.0, 421.0, 419.0])],
    )
    prep = prepare_series_for_openair(data=data, granularity="raw_5m")
    assert "error" not in prep
    assert prep["granularity_effective"] == "raw_5m"
    assert len(prep["timestamps"]) == 3


def test_prepare_invalid_granularity_error():
    """Unknown granularity strings should return a clear error."""
    prep = prepare_series_for_openair(data=_felisa_series(), granularity="raw_xm")
    assert "error" in prep
    assert "raw_Nm" in prep["error"]
