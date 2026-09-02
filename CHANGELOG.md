# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

This repo is versioned together with [openair-3-mcp-client-plugin-oss](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss) — pair matching releases.

## [Unreleased]

### Added

- `CITATION.cff` — machine-readable citation metadata (GitHub "Cite this repository").
- `CONTRIBUTING.md` — dev setup, tool-adding guide, testing tiers, PR process.

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
