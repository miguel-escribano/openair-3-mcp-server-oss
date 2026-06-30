"""Tests for JSON export → prepare bridge."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openair_mcp.export_bridge import (
    export_to_series_v1,
    merge_json_exports,
    resolve_prepare_input,
)
from openair_mcp.prepare import prepare_series_for_openair


def _sample_export(device: str, mean: float) -> dict:
    return {
        "device": device,
        "parameters": [
            {
                "parameter": "o3",
                "unit": "ppb",
                "data": {
                    "2026-06-18 10:00": {"mean": mean},
                    "2026-06-18 11:00": {"mean": mean + 1},
                },
            }
        ],
    }


def test_json_export_single():
    built = export_to_series_v1(_sample_export("Office A", 102.5))
    assert built is not None
    assert built["series"][0]["values"][0] == 102.5


def test_merge_two_devices():
    merged = merge_json_exports(
        [_sample_export("Office A", 100.0), _sample_export("Office B", 200.0)],
        ["o3"],
    )
    assert merged is not None
    assert len(merged["series"]) == 2


def test_resolve_rejects_null_stub():
    stub = {
        "timestamps": [f"2026-06-18T{i:02d}:00:00Z" for i in range(24)],
        "series": [{"name": "o3", "unit": "ppb", "values": [None] * 24}],
    }
    _, _, err = resolve_prepare_input(stub, None, None, None)
    assert err is not None
    assert "no numeric values" in err["error"]


def test_prepare_via_json_exports():
    prep = prepare_series_for_openair(
        json_exports=[_sample_export("Main Office", 102.0)],
        granularity="hourly",
        timezone_name="UTC",
    )
    assert "error" not in prep
    assert prep["data_source"] == "json_export"
    assert any(v is not None for v in prep["values"])
