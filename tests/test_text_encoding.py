"""Tests for UTF-8 mojibake repair in column labels."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openair_mcp.text_encoding import fix_mojibake, normalize_label
from openair_mcp.utils import series_from_csv_text


def test_fix_mojibake_spanish_pollutant_names():
    assert fix_mojibake("DiÃ³xido de nitrÃ³geno (Âµg/mÂ³)") == "Dióxido de nitrógeno (µg/m³)"
    assert fix_mojibake("PartÃ­culas en suspensiÃ³n < 10 Âµm (Âµg/mÂ³)") == (
        "Partículas en suspensión < 10 µm (µg/m³)"
    )
    assert fix_mojibake("Ozono (Âµg/m3)") == "Ozono (µg/m3)"
    assert fix_mojibake("PM10") == "PM10"


def test_series_from_csv_text_repairs_mojibake_headers():
    csv_text = (
        "date,DiÃ³xido de nitrÃ³geno (Âµg/mÂ³),PartÃ­culas en suspensiÃ³n < 10 Âµm (Âµg/mÂ³)\n"
        "2024-01-01T00:00:00Z,10,20\n"
    )
    series = series_from_csv_text(csv_text, datetime_col="date", timezone="UTC")
    names = [col.name for col in series.series]
    assert names[0] == "Dióxido de nitrógeno (µg/m³)"
    assert names[1] == "Partículas en suspensión < 10 µm (µg/m³)"


def test_normalize_label_strips_whitespace():
    assert normalize_label("  PM10  ") == "PM10"
