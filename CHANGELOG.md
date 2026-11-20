# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

This repo is versioned together with [openair-3-mcp-client-plugin-oss](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss) — pair matching releases.

## [Unreleased]

## [0.2.2] - 2026-11-20

### Fixed

- `import_meta` no longer maps generic `pollutants` (import smoke / `import_aurn` only) to `importMeta(pollutant=)`.
- `import_ukaq` uses openair 3.2 `source=` instead of removed `network=` argument.
- `dist_plot` smoke fixture uses NO2; plot uses ggplot2 `title=`; coerce `mydata` to tibble (openair 3.2 `distPlot` + plain `data.frame`).
- `import_meta` maps single site codes (e.g. `MY1`) to `code=`, not pattern `site=` (openair 3.2).

## [0.2.1] - 2026-11-20

### Added

- **`dist_plot`** — openair `distPlot()` wrapper; optional `plot_options.dist_method` and `theme`.
- **`import_meta`** — forwards openair 3.2 `importMeta()` filters (`code`, `site_type`, `meta_pollutant`, `year`, `lat`/`lng`, `max_dist`, `max_n`, `all_meta`, `duplicate`); extended `network` values (`ukaq`, `local`, `imperial`, `all`).
- **Plot themes** — optional `plot_options.theme` or `meta.theme` on SeriesV1/WindSeriesV1/TrajSeriesV1; passed through `prepare_series_for_openair` to all image tools via `openair_plot_call()`.

### Changed

- `ImportParamsV1` — `site` / `start_date` / `end_date` optional at the contract layer (time-series import R scripts still validate dates).

## [0.2.0] - 2026-11-20

### Changed

- Document and validate against **CRAN openair 3.2.0** (ggplot2 4.x backend). Host R must run `openair >= 3.2.0` and `legendry >= 0.3.0` for full `cor_plot` dendrogram support (aligned with openair 3.2.0 Suggests).
- `health_r` and integration smoke expect `legendry >= 0.3.0`.

### Added

- `CITATION.cff` — machine-readable citation metadata (GitHub "Cite this repository").
- `CONTRIBUTING.md` — dev setup, tool-adding guide, testing tiers, PR process.

### Fixed

- Column-id collision in `conditional_quantile` and `taylor_diagram` (`6ed313d`, 2026-08-16). A reused series id is suffixed so obs and model columns of the same pollutant are not the same column. The commit is after content tag 0.1.0 and before `08a7374` (2026-09-02, which added this changelog). It is not a client URL change.

## [0.1.0] - 2026-06-30

Initial public release of the openair MCP server.

### Added

- CSV ingest (`load_series_from_csv`) — EU/ES date formats, optional `columns`, `timezone`, `dedupe_timestamps`.
- Excel ingest (`load_series_from_excel`) — regional `.xlsx` exports (Spanish `Fecha/hora`, duplicate-hour dedupe).
- Upload ingest (`load_series_from_upload`) — base64 CSV/xlsx, 1 MB default limit (`OPENAIR_INGEST_MAX_BYTES`).
- `scripts/export_local_series.py` — client-side local export for remote-MCP setups (no R required on the client).
- Public network import — `import_aurn`, `import_europe`, `import_ukaq`, `import_adms`, `import_aurn_csv`, `import_meta`, `import_traj`.
- Full openair plot/stats surface — 37 R-backed tools: time series, polar/wind, trajectory, stats & transforms.
- `prepare_series_for_openair` — deterministic timestamp/granularity/timezone alignment, DST-safe.
- `SeriesV1`, `WindSeriesV1`, `TrajSeriesV1`, `ImportParamsV1` contracts (`openair_mcp/contracts.py`, mirrored in `schemas/*.json`).
- stdio and HTTP transports; `mcp-remote` support for remote hosting with token auth.
- Utility tools — `ping`, `health_r`, `openair_docs`, `openair_function_help`.
- Auto-discovery of tools from `r/scripts/*.R` manifest headers — no Python change needed to add a tool.
- `pytest` unit suite + `check_integrations.py` host smoke suite.

### Fixed

- DST transition + null-gap crash (`replacement has N rows, data has M rows`) in `time_variation` and related plot tools — DST-safe bucket grid in `openair_mcp/time_grid.py`, `openair_mcp_values()` R helper in `r/common/series_df.R`. Regression coverage: `tests/test_time_grid.py`, `check_integrations.py`.
