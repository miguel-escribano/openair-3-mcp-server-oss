"""Standalone integration check for openair-3-mcp.

Verifies each layer independently without running the MCP server.
Run from the repo root with the venv active:

    python check_integrations.py

R tests are skipped gracefully if R / openair is not installed on this machine.
R is only required on the host where you run this MCP server — not on IDE clients.

Optional env:
  OPENAIR_SMOKE_SLOW=1     — include polar_cluster, traj_cluster (300s each)
  OPENAIR_SMOKE_NETWORK=1 — smoke import_* tools against public networks
"""
from __future__ import annotations

import asyncio
import base64
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp.utilities.types import Image
from fastmcp.tools.tool import _convert_to_content

from openair_mcp.contracts import SeriesColumnV1, SeriesV1, WindSeriesV1
from openair_mcp.r_bridge import (
    R_SCRIPTS_DIR,
    discover_scripts,
    openair_installed,
    r_available,
    r_package_installed,
    run_r_script,
)
from openair_mcp.smoke_fixtures import build_payload, should_skip_tool
from openair_mcp.utils import series_from_csv

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results: list[tuple[str, str]] = []


def check(name: str, fn):
    try:
        msg = fn()
        results.append((PASS, f"{name}: {msg or 'ok'}"))
    except Exception as e:
        results.append((FAIL, f"{name}: {e}"))


def skip(name: str, reason: str):
    results.append((SKIP, f"{name}: {reason}"))


def _count_registered_tools(mcp) -> int:
    if hasattr(mcp, "list_tools"):
        tools = asyncio.run(mcp.list_tools())
        return len(tools)
    if hasattr(mcp, "get_tools"):
        tools = asyncio.run(mcp.get_tools())
        return len(tools)
    raise RuntimeError("FastMCP server has no list_tools/get_tools")


def _check_server_import():
    from server import mcp

    n = _count_registered_tools(mcp)
    if n < 38:
        return (
            f"{n} tools registered (expected ~45 on FastMCP 3.x deploy with 37 R scripts + built-ins; "
            "local FastMCP 2.x may register only built-ins — activate project venv with FastMCP 3.x)"
        )
    return f"{n} tools registered"


check("Python: server imports and registers tools", _check_server_import)


def _check_plot_envelope():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    path = Path(tempfile.gettempdir()) / "openair_smoke_envelope.png"
    path.write_bytes(png)
    blocks = _convert_to_content(["Time variation for CO2", Image(path=path)])
    types = [b.type for b in blocks]
    if types != ["text", "image"]:
        raise RuntimeError(f"expected ['text','image'], got {types}")
    img = blocks[1].model_dump()
    if not img.get("data"):
        raise RuntimeError("image block missing base64 data")
    return f"block order {types}, base64 len={len(img['data'])}"


check("Python: plot envelope [text, image]", _check_plot_envelope)


def _check_contracts():
    s = SeriesV1(
        timestamps=["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
        series=[SeriesColumnV1(name="CO2", unit="ppm", values=[420.0, 415.5])],
    )
    assert len(s.timestamps) == 2
    w = WindSeriesV1(
        timestamps=["2024-01-01T00:00:00Z"],
        series=[SeriesColumnV1(name="NO2", unit="µg/m³", values=[25.0])],
        ws=[3.5],
        wd=[180.0],
    )
    assert len(w.ws) == 1
    return "SeriesV1 and WindSeriesV1 validate"


check("Python: contract validation (SeriesV1, WindSeriesV1)", _check_contracts)


def _check_manifest_discovery():
    scripts = discover_scripts()
    return f"{len(scripts)} scripts with valid manifests in r/scripts/"


check("Python: manifest discovery", _check_manifest_discovery)


def _check_utils_csv():
    import os
    import tempfile

    csv_content = (
        "date,CO2,PM25\n2024-01-01T00:00:00Z,420.1,12.3\n2024-01-01T01:00:00Z,418.5,11.8\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        tmp = f.name
    try:
        s = series_from_csv(tmp)
        assert len(s.timestamps) == 2
        assert len(s.series) == 2
    finally:
        os.unlink(tmp)
    return "series_from_csv parses 2 rows, 2 columns"


check("Python: series_from_csv utility", _check_utils_csv)


def _check_spain_csv_fixture():
    fixture = Path(__file__).parent / "fixtures" / "sample_spain_hourly.csv"
    s = series_from_csv(
        fixture,
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    if len(s.timestamps) != 5:
        raise RuntimeError(f"expected 5 deduped hourly rows, got {len(s.timestamps)}")
    if not s.timestamps[0].endswith("Z"):
        raise RuntimeError("expected UTC Z timestamps")
    return "Spain-style CSV (dd/mm/yyyy + h suffix, dedupe) -> 5 points"


check("Python: Spain/EU CSV datetime + dedupe", _check_spain_csv_fixture)


def _check_upload_spain_csv():
    import base64

    from server import load_series_from_upload

    fixture = Path(__file__).parent / "fixtures" / "sample_spain_hourly.csv"
    b64 = base64.b64encode(fixture.read_bytes()).decode("ascii")
    result = load_series_from_upload(
        content_base64=b64,
        file_type="csv",
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    if "error" in result:
        raise RuntimeError(result["error"])
    if len(result.get("timestamps", [])) != 5:
        raise RuntimeError(f"expected 5 rows, got {len(result.get('timestamps', []))}")
    return "load_series_from_upload (Spain CSV) -> 5 points"


check("Python: load_series_from_upload (Spain CSV)", _check_upload_spain_csv)


def _check_upload_prepare_chain():
    import base64

    from server import load_series_from_upload, prepare_series_for_openair

    fixture = Path(__file__).parent / "fixtures" / "sample_spain_hourly.csv"
    b64 = base64.b64encode(fixture.read_bytes()).decode("ascii")
    loaded = load_series_from_upload(
        content_base64=b64,
        file_type="csv",
        datetime_col="date",
        columns=["PM10"],
        timezone="Europe/Madrid",
    )
    if "error" in loaded:
        raise RuntimeError(loaded["error"])
    prep = prepare_series_for_openair(data=loaded, series_name="PM10")
    if prep.get("data_source") == "error" or "error" in prep:
        raise RuntimeError(prep.get("hint") or prep.get("error") or prep)
    return f"upload -> prepare OK ({len(prep.get('timestamps', []))} buckets)"


check("Python: upload -> prepare_series_for_openair", _check_upload_prepare_chain)


def _check_dst_prepare_payload():
    from openair_mcp.smoke_fixtures import build_dst_gap_payload

    payload = build_dst_gap_payload()
    n = len(payload["timestamps"])
    vals = payload["series"][0]["values"]
    if len(vals) != n:
        raise RuntimeError(f"timestamps={n} values={len(vals)}")
    nulls = sum(1 for v in vals if v is None)
    if nulls < 6:
        raise RuntimeError(f"expected >=6 null gaps, got {nulls}")
    return f"{n} buckets, {nulls} nulls, unique UTC timestamps"


check("Python: DST gap prepare payload", _check_dst_prepare_payload)

ok_r, r_msg = r_available()

if not ok_r:
    skip("R layer", f"R not found ({r_msg})")
else:
    results.append((PASS, f"R available: {r_msg}"))

    ok_o, o_msg = openair_installed()
    if not ok_o:
        skip("R plot/stats smokes", f"openair not installed ({o_msg})")
    else:
        results.append((PASS, f"openair installed: {o_msg}"))

        ok_l, l_msg = r_package_installed("legendry", "0.2.4")
        if ok_l:
            results.append((PASS, f"legendry installed: {l_msg} (cor_plot dendrogram)"))
        else:
            skip(
                "legendry dendrogram",
                f"{l_msg} — cor_plot runs without dendrogram; "
                "install.packages('legendry', repos='https://cloud.r-project.org')",
            )

        def _check_dst_time_variation():
            from openair_mcp.smoke_fixtures import build_dst_gap_payload

            script = R_SCRIPTS_DIR / "time_variation.R"
            payload = build_dst_gap_payload()
            result = run_r_script(script, payload, timeout=90)
            artifact = result.get("artifact", "")
            if not artifact or not Path(artifact).is_file():
                raise RuntimeError("No PNG artifact returned for DST gap fixture")
            return f"PNG {Path(artifact).name} ({len(payload['timestamps'])} points, null gaps)"

        check("R: time_variation DST gaps", _check_dst_time_variation)

        def _check_local_tz_axis():
            # meta.timezone must localize a time-axis plot's axis (display only).
            script = R_SCRIPTS_DIR / "time_plot.R"
            payload = build_payload(
                "time_plot", {"input_type": "series", "output_type": "image"}
            )
            payload = dict(payload)
            payload["meta"] = {"timezone": "Europe/Madrid", "source": "smoke"}
            result = run_r_script(script, payload, timeout=60)
            artifact = result.get("artifact", "")
            if not artifact or not Path(artifact).is_file():
                raise RuntimeError("No PNG artifact for local-tz time_plot")
            return f"PNG {Path(artifact).name} (axis localized to Europe/Madrid)"

        check("R: time_plot local timezone axis", _check_local_tz_axis)

        for script_path, manifest in discover_scripts():
            tool_name = manifest["name"]
            output_type = manifest.get("output_type", "image")
            timeout = int(manifest.get("timeout", 60))

            slow_reason = should_skip_tool(tool_name)
            if slow_reason:
                skip(f"R: {tool_name}", slow_reason)
                continue

            payload = build_payload(tool_name, manifest)
            if payload is None:
                skip(
                    f"R: {tool_name}",
                    "import/network smoke skipped — set OPENAIR_SMOKE_NETWORK=1",
                )
                continue

            def _run(script=script_path, pl=payload, ot=output_type, to=timeout, tn=tool_name):
                result = run_r_script(script, pl, timeout=to)
                if ot == "image":
                    artifact = result.get("artifact", "")
                    if not artifact or not Path(artifact).is_file():
                        raise RuntimeError("No PNG artifact returned")
                    return f"PNG {Path(artifact).name}"
                if ot == "stats":
                    if not result.get("summary") and not result.get("stats"):
                        raise RuntimeError("No stats/summary in JSON")
                    return (result.get("summary") or "stats ok")[:80]
                if ot == "series":
                    if not result.get("timestamps") and not result.get("series"):
                        raise RuntimeError("No series JSON returned")
                    n = len(result.get("timestamps") or [])
                    return f"series JSON, {n} timestamps"
                raise RuntimeError(f"unknown output_type {ot}")

            check(f"R: {tool_name}", _run)

print()
print("=" * 60)
print("openair-3-mcp integration check")
print("=" * 60)
for status, msg in results:
    print(f"  {status} {msg}")

failures = [r for r in results if r[0] == FAIL]
passes = [r for r in results if r[0] == PASS]
skips = [r for r in results if r[0] == SKIP]

print()
print(f"  {len(passes)} passed  |  {len(skips)} skipped  |  {len(failures)} failed")
print()

if failures:
    sys.exit(1)
