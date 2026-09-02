# Contributing to openair-3-mcp-server-oss

Thanks for considering a contribution. This repo is the **server** half of the openair MCP binomio — see [openair-3-mcp-client-plugin-oss](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss) for the client plugin, and [openair-ai-kit](https://github.com/miguel-escribano/openair-ai-kit) for the landing page.

## Scope

This project provides **charts and data access** through MCP, powered by [openair](https://github.com/openair-project/openair) on R. It intentionally stays out of:

- Interpretation, compliance advice, or health guidance (that belongs in your own reporting layer)
- Vendor-specific integrations (this is a generic openair MCP — CSV, public imports, `SeriesV1` JSON)

Changes that pull the server toward either of those are likely to be redirected rather than merged — open an issue first if you're unsure whether an idea fits.

## Development setup

```bash
git clone https://github.com/miguel-escribano/openair-3-mcp-server-oss
cd openair-3-mcp-server-oss
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
python check_integrations.py
```

Install R (4.1+) and the `openair` 3.x + `jsonlite` packages on the same machine — see the [README Quick start](README.md#quick-start).

## Adding a tool

Tools are **auto-discovered** at startup from `r/scripts/` — no Python change required:

1. Create `r/scripts/<name>.R` with a `# MANIFEST: {...}` header on the first line (JSON in, JSON/PNG out).
2. Restart the server. `server.py` scans `r/scripts/`, parses the manifest, and registers the tool.

Shared R helpers live in `r/common/`. `openair_mcp/contracts.py` is the source of truth for input/output Pydantic types (`SeriesV1`, `WindSeriesV1`, `TrajSeriesV1`, `ImportParamsV1`) — `schemas/*.json` mirrors them for non-Python readers.

**Breaking a contract?** Ship a new version suffix (e.g. `SeriesV2`) — never overwrite `V1` in place. Downstream clients (including the paired plugin repo) depend on the existing shape.

## Testing

Three tiers — run all of them before proposing a release-worthy change:

| Tier | Command | Covers |
|------|---------|--------|
| **Unit** | `pytest` | Ingest, prepare, encoding, DST — fast, mostly no R required |
| **Host smoke** | `python check_integrations.py` | Tool registration + R subprocess when R is installed |
| **Acceptance** | [plugin repo `tests/`](https://github.com/miguel-escribano/openair-3-mcp-client-plugin-oss/tree/main/tests) | 12+4 plots against a **deployed** MCP — legends, encoding, end-to-end |

Fixtures in `fixtures/` are for pytest and `check_integrations.py` only — not chat/demo datasets.

## Code style

- Python 3.11+, `ruff` for linting (`ruff check .`), 100-char line length — see `[tool.ruff]` in `pyproject.toml`.
- Keep tool wrappers thin: parsing/validation in Python (`openair_mcp/`), computation in R (`r/scripts/`).

## Submitting changes

1. Open an issue first for anything beyond a small fix — especially new tools, contract changes, or anything touching scope.
2. Keep PRs focused — one tool, one fix, one doc change per PR where practical.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Make sure `pytest` and `check_integrations.py` pass locally before opening the PR.
5. If your change affects the client plugin's expectations (new tool, changed contract), flag it in the PR description — the two repos are versioned together per release.

## Reporting bugs / requesting features

Use [GitHub issues](https://github.com/miguel-escribano/openair-3-mcp-server-oss/issues). Include: transport (stdio/HTTP), R version (`health_r` output if available), and the tool name + input shape that triggered the problem.

## Attribution

This project is **not affiliated** with [openair-project](https://github.com/openair-project/openair) maintainers. If your contribution adds a wrapper around a new openair function, keep the citation and license notes in [NOTICE.md](NOTICE.md) accurate.

## License

By contributing, you agree your contribution is licensed under the [MIT License](LICENSE) that covers this repo.
