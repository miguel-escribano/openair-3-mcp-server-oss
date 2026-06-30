"""openair-3-mcp — FastMCP server wrapping the R openair package.

Tools are discovered automatically from r/scripts/*.R manifest headers at startup.
One R script = one MCP tool. No code change required to add new tools.

Run:
  fastmcp run server.py:mcp --transport http --port 8001   # HTTP (remote)
  fastmcp run server.py:mcp                                  # stdio (Claude Desktop)
  python server.py                                           # respects OPENAIR_MCP_TRANSPORT env
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.types import Image
from mcp.types import TextContent

load_dotenv()

from openair_mcp.contracts import (
    ArtifactV1,
    ImportFileParamsV1,
    ImportParamsV1,
    SeriesV1,
    StatsResultV1,
    TrajSeriesV1,
    WindSeriesV1,
)
from openair_mcp.r_bridge import (
    R_SCRIPTS_DIR,
    discover_scripts,
    openair_installed,
    r_available,
    r_package_installed,
    run_r_script,
)

_INPUT_TYPES = {
    "series": SeriesV1,
    "wind_series": WindSeriesV1,
    "traj_series": TrajSeriesV1,
    "import_params": ImportParamsV1,
    "file_import": ImportFileParamsV1,
}

_OUTPUT_TYPES = {"image", "stats", "series"}
from openair_mcp.prepare import prepare_series_for_openair as _run_prepare_series


def _make_plot_tool(script_path: Path, manifest: dict):
    """Factory: returns a typed function that runs a plot R script → [text, image] MCP blocks."""
    input_cls = _INPUT_TYPES.get(manifest.get("input_type", "series"), SeriesV1)
    timeout = manifest.get("timeout", 60)
    tool_name = manifest["name"]

    def tool_fn(data: input_cls) -> ToolResult:
        payload = data.model_dump(mode="json")
        result = run_r_script(script_path, payload, timeout=timeout)
        artifact = ArtifactV1.model_validate({**result, "tool": tool_name})
        image = Image(path=artifact.artifact)
        return ToolResult(
            content=[
                TextContent(type="text", text=artifact.summary),
                image.to_image_content(),
            ]
        )

    tool_fn.__name__ = tool_name
    tool_fn.__doc__ = manifest.get("description", f"openair::{tool_name}")
    tool_fn.__annotations__ = {"data": input_cls, "return": ToolResult}
    return tool_fn


def _make_stats_tool(script_path: Path, manifest: dict):
    """Factory: returns a typed function that runs a stats R script → StatsResultV1."""
    input_cls = _INPUT_TYPES.get(manifest.get("input_type", "series"), SeriesV1)
    timeout = manifest.get("timeout", 60)
    tool_name = manifest["name"]

    def tool_fn(data: input_cls) -> dict:
        payload = data.model_dump(mode="json")
        result = run_r_script(script_path, payload, timeout=timeout)
        return result

    tool_fn.__name__ = tool_name
    tool_fn.__doc__ = manifest.get("description", f"openair::{tool_name}")
    tool_fn.__annotations__ = {"data": input_cls, "return": dict}
    return tool_fn


def _make_import_tool(script_path: Path, manifest: dict):
    """Factory: returns a typed function that runs an import R script (ImportParamsV1 in → SeriesV1 JSON out)."""
    timeout = manifest.get("timeout", 120)
    tool_name = manifest["name"]

    def tool_fn(params: ImportParamsV1) -> dict:
        payload = params.model_dump(mode="json")
        result = run_r_script(script_path, payload, timeout=timeout)
        return result

    tool_fn.__name__ = tool_name
    tool_fn.__doc__ = manifest.get("description", f"openair import::{tool_name}")
    tool_fn.__annotations__ = {"params": ImportParamsV1, "return": dict}
    return tool_fn


def _make_file_import_tool(script_path: Path, manifest: dict):
    """Factory: file-path import (ADMS, AURN CSV) → SeriesV1 JSON."""
    timeout = manifest.get("timeout", 120)
    tool_name = manifest["name"]

    def tool_fn(params: ImportFileParamsV1) -> dict:
        payload = params.model_dump(mode="json")
        result = run_r_script(script_path, payload, timeout=timeout)
        return result

    tool_fn.__name__ = tool_name
    tool_fn.__doc__ = manifest.get("description", f"openair file import::{tool_name}")
    tool_fn.__annotations__ = {"params": ImportFileParamsV1, "return": dict}
    return tool_fn


def _make_series_transform_tool(script_path: Path, manifest: dict):
    """Factory: returns a typed function that transforms a SeriesV1 → SeriesV1 JSON (e.g. time_average, rolling_mean)."""
    input_cls = _INPUT_TYPES.get(manifest.get("input_type", "series"), SeriesV1)
    timeout = manifest.get("timeout", 60)
    tool_name = manifest["name"]

    def tool_fn(data: input_cls) -> dict:
        payload = data.model_dump(mode="json")
        result = run_r_script(script_path, payload, timeout=timeout)
        return result

    tool_fn.__name__ = tool_name
    tool_fn.__doc__ = manifest.get("description", f"openair::{tool_name}")
    tool_fn.__annotations__ = {"data": input_cls, "return": dict}
    return tool_fn


mcp = FastMCP(
    "openair-3-mcp",
    instructions=(
        "Air quality analysis via the R openair package. "
        "Plot tools return PNG images with a leading text summary. Stats tools return JSON. "
        "Import tools fetch data from public monitoring networks (AURN, Europe) "
        "or openair file formats on server disk (import_adms, import_aurn_csv). "
        "Load CSV or Excel from the server disk (load_series_from_*) or upload small files "
        "(load_series_from_upload, base64, max 1 MB raw). "
        "Wind/polar tools require ws and wd columns. "
        "Trajectory tools require HYSPLIT-format trajectory data. "
        "Use openair_docs and openair_function_help for official docs/book links."
    ),
)


@mcp.tool
def ping() -> dict:
    """Health check — Python layer only."""
    from openair_mcp import __version__
    return {"status": "ok", "service": "openair-3-mcp", "version": __version__}


@mcp.tool
def health_r() -> dict:
    """Check R runtime, openair, and optional plot dependencies on this host."""
    ok_r, r_msg = r_available()
    ok_o, o_msg = openair_installed() if ok_r else (False, "skipped")
    ok_l, l_msg = (
        r_package_installed("legendry", "0.2.4") if ok_r else (False, "skipped")
    )
    return {
        "r": ok_r,
        "r_detail": r_msg,
        "openair": ok_o,
        "openair_detail": o_msg,
        "legendry": ok_l,
        "legendry_detail": l_msg,
        "cor_plot_dendrogram": ok_l,
    }


@mcp.tool
def load_series_from_csv(
    path: str,
    datetime_col: str = "date",
    columns: list[str] | None = None,
    timezone: str = "UTC",
    site: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    dedupe_timestamps: bool = True,
) -> dict:
    """Load a wide CSV from the **server filesystem** into SeriesV1 JSON.

    Rows = timestamps; columns = pollutants (and optional metadata — use
    ``columns`` to pick PM2.5, NO2, etc.). Path must exist on the machine
    running openair-3-mcp.

    Accepts ISO-8601 and common EU day-first timestamps (e.g. ``23/06/2026 00:00h``).
    Naive values use ``timezone`` (IANA, e.g. ``Europe/Madrid``). Duplicate timestamps
    after parsing are deduplicated (keep last) when ``dedupe_timestamps`` is true.
    Optional ``lat`` / ``lon`` (WGS84) are stored in ``meta`` for future meteo merge (worldmet).
    """
    from openair_mcp.utils import series_from_csv

    try:
        series = series_from_csv(
            path,
            datetime_col=datetime_col,
            columns=columns,
            timezone=timezone,
            site=site,
            lat=lat,
            lon=lon,
            dedupe_timestamps=dedupe_timestamps,
        )
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    return series.model_dump(mode="json")


@mcp.tool
def load_series_from_excel(
    path: str,
    sheet_name: str | None = None,
    datetime_col: str = "date",
    columns: list[str] | None = None,
    timezone: str = "UTC",
    site: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    dedupe_timestamps: bool = True,
) -> dict:
    """Load a wide Excel (.xlsx) file from the **server filesystem** into SeriesV1 JSON.

    Same semantics as ``load_series_from_csv`` — first row = headers, one datetime column,
    one or more pollutant columns. Typical for government / network exports (Spain, EU).
    Optional ``lat`` / ``lon`` (WGS84) stored in ``meta`` for future meteo merge (worldmet).
    """
    from openair_mcp.utils import series_from_excel

    try:
        series = series_from_excel(
            path,
            sheet_name=sheet_name,
            datetime_col=datetime_col,
            columns=columns,
            timezone=timezone,
            site=site,
            lat=lat,
            lon=lon,
            dedupe_timestamps=dedupe_timestamps,
        )
    except (FileNotFoundError, ValueError, ImportError) as exc:
        return {"error": str(exc)}
    return series.model_dump(mode="json")


@mcp.tool
def load_series_from_upload(
    content_base64: str,
    file_type: Literal["csv", "xlsx"],
    datetime_col: str = "date",
    columns: list[str] | None = None,
    timezone: str = "UTC",
    site: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    sheet_name: str | None = None,
    dedupe_timestamps: bool = True,
) -> dict:
    """Load CSV or Excel content uploaded as base64 into SeriesV1 JSON.

    Use when the file is on the user's machine and the MCP server runs remotely.
    Raw decoded size must be at most 1 MB (override via OPENAIR_INGEST_MAX_BYTES on the server).
    Same parsing options as ``load_series_from_csv`` / ``load_series_from_excel``.
    Optional ``lat`` / ``lon`` (WGS84) stored in ``meta`` for future meteo merge (worldmet).
    """
    from openair_mcp.utils import (
        INGEST_MAX_BYTES,
        series_from_csv_text,
        series_from_excel_bytes,
    )

    try:
        raw = base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        return {"error": f"Invalid base64 content: {exc}"}

    if len(raw) > INGEST_MAX_BYTES:
        return {
            "error": (
                f"Upload exceeds {INGEST_MAX_BYTES} bytes. "
                "Copy the file to the server disk and use load_series_from_csv or "
                "load_series_from_excel instead."
            )
        }

    try:
        if file_type == "csv":
            text = raw.decode("utf-8-sig")
            series = series_from_csv_text(
                text,
                datetime_col=datetime_col,
                columns=columns,
                timezone=timezone,
                site=site,
                lat=lat,
                lon=lon,
                dedupe_timestamps=dedupe_timestamps,
            )
        elif file_type == "xlsx":
            series = series_from_excel_bytes(
                raw,
                sheet_name=sheet_name,
                datetime_col=datetime_col,
                columns=columns,
                timezone=timezone,
                site=site,
                lat=lat,
                lon=lon,
                dedupe_timestamps=dedupe_timestamps,
            )
        else:
            return {"error": f"Unsupported file_type: {file_type!r}. Use 'csv' or 'xlsx'."}
    except (ValueError, ImportError, UnicodeDecodeError) as exc:
        return {"error": str(exc)}

    return series.model_dump(mode="json")


@mcp.tool
def prepare_series_for_openair(
    data: SeriesV1 | None = None,
    json_exports: list[dict] | None = None,
    series_name: str | None = None,
    parameter: str | None = None,
    granularity: str = "hourly",  # hourly | daily | weekly | monthly | raw_Nm (e.g. raw_5m, raw_15m, raw_30m)
    timezone_name: str = "UTC",
    gap_policy: str = "preserve",
    coverage_threshold: float = 0.9,
    max_points: int = 10000,
) -> dict:
    """Prepare deterministic aligned timestamps/values for OpenAir plotting.

    Provide **either**:
    - ``data``: SeriesV1 from ``load_series_from_csv``, ``load_series_from_excel``,
      ``load_series_from_upload``, or ``import_*`` tools, **or**
    - ``json_exports``: optional list of JSON export payloads from another MCP (advanced).

    Use ``series_name`` when ``data`` contains multiple pollutant columns.
    Do not pass null placeholder arrays.
    """
    return _run_prepare_series(
        data,
        json_exports=json_exports,
        series_name=series_name,
        parameter=parameter,
        granularity=granularity,
        timezone_name=timezone_name,
        gap_policy=gap_policy,
        coverage_threshold=coverage_threshold,
        max_points=max_points,
    )


@mcp.tool
def openair_docs() -> dict:
    """Official openair documentation links (package, reference, book)."""
    return {
        "package_repo": "https://github.com/openair-project/openair",
        "reference_index": "https://openair-project.github.io/openair/reference/index.html",
        "book_repo": "https://github.com/openair-project/book",
        "book_site": "https://openair-project.github.io/book/",
        "latest_release_hint": (
            "Check releases in package_repo to confirm recent API changes "
            "before adding/manifests for new functions."
        ),
    }


@mcp.tool
def openair_function_help(function_name: str) -> dict:
    """Return canonical docs URLs for one openair function name."""
    fn = (function_name or "").strip()
    if not fn:
        return {
            "error": "function_name is required, e.g. 'timePlot', 'polarPlot', 'timeAverage'."
        }
    return {
        "function_name": fn,
        "reference_url": f"https://openair-project.github.io/openair/reference/{fn}.html",
        "book_search_url": f"https://openair-project.github.io/book/search.html?q={fn}",
    }


def _register_tools() -> int:
    """Scan r/scripts/, parse manifests, register one tool per script."""
    scripts = discover_scripts()
    registered = 0
    for script_path, manifest in scripts:
        output_type = manifest.get("output_type", "image")
        input_type = manifest.get("input_type", "series")
        try:
            if output_type == "image":
                fn = _make_plot_tool(script_path, manifest)
            elif output_type == "stats":
                fn = _make_stats_tool(script_path, manifest)
            elif output_type == "series" and input_type == "import_params":
                fn = _make_import_tool(script_path, manifest)
            elif output_type == "series" and input_type == "file_import":
                fn = _make_file_import_tool(script_path, manifest)
            elif output_type == "series":
                # Series-in / series-out transforms (time_average, rolling_mean, etc.)
                fn = _make_series_transform_tool(script_path, manifest)
            else:
                print(f"WARN: unknown output_type '{output_type}' in {script_path.name}, skipping")
                continue
            mcp.add_tool(fn)
            registered += 1
        except Exception as e:
            print(f"ERR  Failed to register tool from {script_path.name}: {e}")
    return registered


_n = _register_tools()
_BUILTIN_TOOLS = 8
print(
    f"openair-3-mcp: registered {_n} dynamic tools + {_BUILTIN_TOOLS} built-in "
    "(ping, health_r, load_series_from_csv, load_series_from_excel, "
    "load_series_from_upload, prepare_series_for_openair, openair_docs, openair_function_help)"
)


if __name__ == "__main__":
    transport = os.getenv("OPENAIR_MCP_TRANSPORT", "stdio")
    port = int(os.getenv("OPENAIR_MCP_PORT", "8001"))
    if transport == "http":
        mcp.run(transport="http", port=port)
    else:
        mcp.run()
