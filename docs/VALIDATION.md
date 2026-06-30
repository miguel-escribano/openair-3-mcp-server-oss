# Validation checklist

## Scope

- **In repo:** Python smoke (`check_integrations.py`), unit tests (`pytest`), CSV/Excel/upload → prepare pipeline, docs.
- **Plugin repo (acceptance):** 15-tool Felisa harness against **deployed** MCP — plots, legends, encoding. See [plugin tests/README.md](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss/blob/main/tests/README.md).
- **On your host (when you choose to deploy):** R + openair 3.x for plot/import smoke and IDE end-to-end tests.
- **Not included:** no hosted MCP — bring your own server (localhost, cloud VM, lab, etc.).

Server `fixtures/*.csv` are **pytest samples only** — not Copilot chat data. Golden dataset: plugin `tests/fixtures/felisa_munarriz.json`.

## Validation tiers (what "tested" means)

Not all 45 tools carry the same validation depth — be explicit about it:

- **Golden-path validated (~15):** the 11 pollutant tools + 4 wind tools exercised end-to-end against a deployed server via the plugin Felisa harness (`time_plot`, `calendar_plot`, `time_variation`, `trend_level`, `scatter_plot`, `cor_plot`, `aq_stats`, `smooth_trend`, `rolling_mean`, `time_average`, plus the wind/polar set).
- **Smoke-only (the rest):** registered and run on synthetic payloads by `check_integrations.py` (and the `r-smoke` CI workflow) — verifies the tool wires up and returns a PNG/JSON, not scientific correctness on real data. Includes the heavier/rarer tools (`polar_cluster`, `traj_*`, `taylor_diagram`, `conditional_quantile`, …).

Availability is not a maturity claim; treat smoke-only tools as functional but unvalidated against a real golden path.

## Server setup

```bash
cd openair-3-mcp-server-oss
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
python check_integrations.py
pytest tests/ -q
```

Optional:

```bash
OPENAIR_SMOKE_NETWORK=1 python check_integrations.py
```

Requires R + openair 3.x on the host for plot/import smoke.

## Prepare meta

```bash
pytest tests/test_prepare.py -q
```

Asserts `meta.site` and timezone propagate through `prepare_series_for_openair`.

## CSV flow

```bash
python -c "
from pathlib import Path
from server import load_series_from_csv, prepare_series_for_openair
p = Path('fixtures/sample_hourly.csv').resolve()
d = load_series_from_csv(str(p), columns=['PM25'])
prep = prepare_series_for_openair(data=d, series_name='PM25')
assert 'error' not in prep
assert 'meta' in prep
print('OK', len(prep['timestamps']))
"
```

## Upload flow

```bash
python -c "
import base64
from pathlib import Path
from server import load_series_from_upload, prepare_series_for_openair
p = Path('fixtures/sample_spain_hourly.csv').read_bytes()
b64 = base64.b64encode(p).decode('ascii')
d = load_series_from_upload(content_base64=b64, file_type='csv', datetime_col='date', columns=['PM10'], timezone='Europe/Madrid')
assert 'error' not in d
prep = prepare_series_for_openair(data=d, series_name='PM10')
assert prep.get('meta')
print('OK', len(prep['timestamps']))
"
```

## Felisa golden path (remote MCP)

Harness lives in the **plugin repo**: `openair-3-mcp-client-plugin-oss/tests/`.

```bash
pip install httpx
export OPENAIR_MCP_TOKEN=…
cd openair-3-mcp-client-plugin-oss
python tests/run_series_exercises.py   # 11 exercises → tests/output/series/
python tests/run_wind_exercises.py     # 4 wind plots → tests/output/wind/
```

Fixture: `tests/fixtures/felisa_munarriz.json` (WindSeriesV1 — pollutants + ERA5 ws/wd).

Visual check: `tests/output/series/02_time_plot_all.png` — legends NO₂ / PM₁₀ / O₃; title includes site + date range. Stats: `08_aq_stats_pm10.json` → `"pollutant": "pm10"`.

**VS Code Copilot:** [vscode-chat-felisa.md](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss/blob/main/examples/vscode-chat-felisa.md) — do not use phantom paths like `data/felisa.xlsx`.

## Rotxapea golden path

export → `prepare_series_for_openair` → `time_plot` (manual or scripted).

## Regression: DST + null gaps

```bash
python -m pytest tests/test_time_grid.py tests/test_export_bridge.py tests/test_ingest_utils.py tests/test_prepare.py -q
```

## IDE smoke (manual)

Fresh session → connect MCP → one of:

| Setup | Path |
|-------|------|
| **VS Code + remote MCP** | [vscode-chat-felisa.md](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss/blob/main/examples/vscode-chat-felisa.md) (committed fixture) |
| **Local stdio + server CSV** | `load_series_from_csv` on a path **on the server host** → prepare → one plot |
| **Public network** | `import_aurn` → prepare → one plot |

PNG renders with readable legend (short pollutant ids, not mojibake).
