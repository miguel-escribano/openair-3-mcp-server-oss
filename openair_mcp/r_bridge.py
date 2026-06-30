"""Invoke R / openair via subprocess. No Python reimplementation of openair."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
R_SCRIPTS_DIR = REPO_ROOT / "r" / "scripts"

_MANIFEST_RE = re.compile(r"^#\s*MANIFEST:\s*(\{.*\})\s*$")


def rscript_path() -> str:
    return os.getenv("RSCRIPT_PATH", "Rscript")


def r_available() -> tuple[bool, str]:
    exe = rscript_path()
    if not shutil.which(exe) and not Path(exe).is_file():
        return False, f"Rscript not found: {exe}"
    try:
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "Rscript --version failed").strip()
    first_line = (proc.stdout or "").splitlines()[0] if proc.stdout else "ok"
    return True, first_line


def openair_installed() -> tuple[bool, str]:
    """Return (ok, version_or_error) after checking library(openair) in R."""
    ok, msg = r_available()
    if not ok:
        return False, msg
    script = (
        "suppressPackageStartupMessages({"
        "  ok <- requireNamespace('openair', quietly=TRUE); "
        "  if (!ok) quit(status=1); "
        "  cat(as.character(packageVersion('openair')))"
        "})"
    )
    proc = subprocess.run(
        [rscript_path(), "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "openair not installed").strip()
        return False, err
    version = (proc.stdout or "").strip()
    return True, version or "unknown"


def r_package_installed(package: str, min_version: str | None = None) -> tuple[bool, str]:
    """Return (ok, version_or_error) for an installed R package."""
    ok, msg = r_available()
    if not ok:
        return False, msg
    min_clause = ""
    if min_version:
        min_clause = (
            f" if (packageVersion('{package}') < '{min_version}') "
            f"stop('need>={min_version}')"
        )
    script = (
        "suppressPackageStartupMessages({"
        f"  ok <- requireNamespace('{package}', quietly=TRUE); "
        "  if (!ok) quit(status=1); "
        f"  cat(as.character(packageVersion('{package}')));"
        f"{min_clause}"
        "})"
    )
    proc = subprocess.run(
        [rscript_path(), "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"{package} not installed").strip()
        return False, err
    version = (proc.stdout or "").strip()
    return True, version or "unknown"


def parse_manifest(script_path: Path) -> dict:
    """Read the MANIFEST JSON from the first comment line of an R script.

    Expected format (first non-empty line of file):
        # MANIFEST: {"name": "...", "description": "...", "input_type": "series", ...}

    Returns empty dict if no manifest found.
    """
    try:
        with open(script_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = _MANIFEST_RE.match(line)
                if m:
                    return json.loads(m.group(1))
                break  # manifest must be first non-empty line
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def discover_scripts() -> list[tuple[Path, dict]]:
    """Return (script_path, manifest) for all R scripts in r/scripts/ that have a valid manifest."""
    results = []
    for script in sorted(R_SCRIPTS_DIR.glob("*.R")):
        manifest = parse_manifest(script)
        if manifest.get("name"):
            results.append((script, manifest))
    return results


def run_r_script(script_path: Path, payload: dict, timeout: int | None = None) -> dict:
    """Run an R script with JSON on stdin; expect JSON on stdout."""
    if not script_path.is_file():
        raise FileNotFoundError(f"R script not found: {script_path}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OPENAIR_ARTIFACTS_DIR"] = str(ARTIFACTS_DIR.resolve())
    env["OPENAIR_R_LIB"] = str((REPO_ROOT / "r" / "common").resolve())

    effective_timeout = timeout or int(os.getenv("RSCRIPT_TIMEOUT_SEC", "60"))

    proc = subprocess.run(
        [rscript_path(), str(script_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=effective_timeout,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            (proc.stderr or proc.stdout or f"R script failed: {script_path.name}").strip()
        )
    # R graphics can emit "null device\n1\n" to stdout before the JSON result.
    # Try parsing the full output first; if that fails, scan from the bottom
    # for the last line that looks like a JSON object.
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        for line in reversed((proc.stdout or "").splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        raise RuntimeError(f"R script returned non-JSON: {(proc.stdout or '')[:500]}")
