# R scripts

Each `.R` file in `scripts/` is one MCP tool, auto-discovered at server startup.

## Requirements (server only — not on the client)

```r
install.packages(c("openair", "jsonlite", "legendry"))
```

Example (Linux server):
```bash
sudo apt-get install r-base
Rscript -e "install.packages(c('openair', 'jsonlite', 'legendry'), repos='https://cloud.r-project.org')"
```

## Script format

Each script must start with a manifest comment line:

```r
# MANIFEST: {"name": "tool_name", "description": "...", "input_type": "series", "output_type": "image", "timeout": 60}
```

- `input_type`: `series` | `wind_series` | `traj_series` | `import_params` | `file_import`
- `output_type`: `image` (returns ArtifactV1 JSON) | `stats` (returns stats JSON) | `series` (returns SeriesV1 JSON)
- `timeout`: seconds (default 60; use higher for slow tools like polar_cluster)

Scripts read JSON from stdin, write JSON to stdout. PNG files are written to `OPENAIR_ARTIFACTS_DIR` (set by the Python layer).

Shared helpers in `common/series_df.R`:

- **`openair_series_col_id`** — maps regional headers (e.g. Spanish portal strings) to lowercase openair column ids (`pm10`, `pm25`, `no2`, `o3`). Repairs UTF-8 mojibake before matching. Let `auto.text` format subscripts in legends.
- **`openair_fix_mojibake` / `openair_normalize_label`** — repair Latin-1 misreads of UTF-8 (e.g. `DiÃ³xido` → `Dióxido`).
- **`openair_plot_title`** — builds title from `meta.site`, series, date range, and `meta.timezone`.
- **`openair_build_series_df`** — SeriesV1 JSON → `data.frame` for time-series plots.
- **`openair_build_wind_df`** — wind tools: `date`, `ws`, `wd`, optional pollutants, optional `site` from meta.
- **`openair_summary_labels`** — short pollutant ids for MCP text summaries (not for `name.pol` legends).
- **`openair_df_to_seriesv1`** — shared import helper: UTC timestamps, pollutant series, meta; excludes coord/meteo columns.
- **`openair_meta_out`** — pass `meta` (and timezone) through series-out transform tools.

**SeriesV1 naming:** `series[].name` keeps the chef's original header (e.g. `PM10` from CSV). R column ids are separate (lowercase `pm10`).

**Testing:** R helpers here are covered by plugin acceptance harness (`openair-3-mcp-client-plugin-oss/tests/`) and server `check_integrations.py` — not by server `fixtures/` alone.

## File imports (server disk)

`import_adms` and `import_aurn_csv` use `input_type: file_import`. The `path` must exist on the MCP server host — not on the IDE client.

## openair reference

- `https://openair-project.github.io/openair/reference/index.html`
- `https://github.com/openair-project/book/`
