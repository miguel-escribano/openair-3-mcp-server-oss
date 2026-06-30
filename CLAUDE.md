# openair-3-mcp — agent notes

MCP server (FastMCP 3.x) wrapping the R openair package. See `README.md` for full tool catalogue and setup.

## References

- openair R package: `https://github.com/openair-project/openair`
- openair reference: `https://openair-project.github.io/openair/reference/index.html`
- openair book: `https://github.com/openair-project/book/`
- FastMCP docs: `https://gofastmcp.com/llms.txt`

## Architecture

Tools are **auto-discovered** at startup from `r/scripts/`. Each `.R` file with a valid `# MANIFEST:` header becomes one MCP tool. No Python change needed to add a tool.

`server.py` → scans `r/scripts/` → parses manifests → `mcp.add_tool()` per script.

## Boundaries

- Generic openair MCP — CSV, public imports, SeriesV1 JSON. No vendor-specific integrations.
- Any MCP client connects via HTTP/SSE endpoint (+ optional token).

## Input/output types

| `input_type` in manifest | Pydantic class | Use for |
|--------------------------|----------------|---------|
| `series` | `SeriesV1` | All non-wind tools |
| `wind_series` | `WindSeriesV1` | Polar/directional tools |
| `traj_series` | `TrajSeriesV1` | Trajectory tools |
| `import_params` | `ImportParamsV1` | Import tools |

| `output_type` | Return value | Use for |
|---------------|-------------|---------|
| `image` | `ToolResult([summary text, Image])` → MCP `[text, image]` | All plot tools |
| `stats` | `dict` (JSON) | Stats/utility tools |
| `series` | `dict` (SeriesV1-shaped JSON) | Import tools |

## Built-in documentation tools

- `openair_docs()` returns official documentation entry points:
  - package repo
  - reference index
  - openair book (repo + published site)
- `openair_function_help(function_name)` returns canonical URLs for one function.
- `prepare_series_for_openair(data, ...)` prepares aligned deterministic
  timestamps/values before plotting. Data must come from load/upload/import tools
  or `json_exports` from another MCP — never client-built arrays.
- `load_series_from_upload(content_base64, file_type, ...)` parses CSV/xlsx uploaded
  as base64 (max 1 MB raw; see `INGEST_MAX_BYTES` in `openair_mcp/utils.py`).

Use these before implementing or updating wrappers for newly added openair functions.

## Known bugs (fixed 2026-05)

### DST transition + null gaps → row-count crash (fixed)

Previously `time_variation` and other plot tools crashed with
`replacement has N rows, data has M rows` when a series crossed a DST boundary
with `gap_policy=preserve` nulls.

**Root causes (both fixed):**

1. `prepare_series_for_openair` advanced local buckets with `+ timedelta(hours=1)`,
   emitting a phantom hour at spring-forward (duplicate UTC timestamp).
2. R scripts used `as.numeric(unlist(values))`, which dropped JSON `null` gaps.

**Fix:** DST-safe bucket grid in `openair_mcp/time_grid.py`; R helper
`openair_mcp_values()` in `r/common/series_df.R` (sourced via `OPENAIR_R_LIB`).

Regression: `tests/test_time_grid.py`, `check_integrations.py` →
`R: time_variation DST gaps`.

## Quick troubleshooting

- If tool registration fails with schema/runtime errors, run the server with the
  project venv Python and verify with `python check_integrations.py`.
- For plotting, prefer deterministic aligned input from
  `prepare_series_for_openair` before calling `time_plot`.
- If production endpoint is unstable, verify with `health_r` and `python check_integrations.py` on the server host.
- If plot fails with `replacement has N rows, data has M rows`, redeploy latest
  openair-3-mcp (DST grid + `openair_mcp_values` fix — see **Known bugs** above).

## Adding a tool

1. Create `r/scripts/<name>.R` — manifest on first line, JSON in, JSON/PNG out.
2. Restart server. Done.

## Contracts

`openair_mcp/contracts.py` is the source of truth. `schemas/*.json` mirrors for non-Python readers. Breaking changes → new version suffix (V2), never overwrite V1.

## Run

```bash
fastmcp run server.py:mcp --transport http --port 8001
```

Verify:

```bash
python check_integrations.py
```
