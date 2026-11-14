"""Ruff lint + format entrypoints for auctelis tooling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from auctelis.paths import repo_root


def _python_roots() -> list[Path]:
    tools = repo_root() / "tools"
    return [tools / "auctelis", repo_root() / "tests"]


def run_ruff(
    *,
    fix: bool = False,
    format_code: bool = False,
    check_format: bool = False,
) -> dict[str, Any]:
    """Run Ruff against package + tests. Returns a machine-readable summary."""
    roots = [str(path) for path in _python_roots() if path.exists()]
    if not roots:
        return {"ok": False, "error": "no Python roots found", "commands": []}

    # Pin the config so results do not depend on the caller's cwd: Ruff otherwise
    # falls back to line-length 88 when run from the repo root and 100 from tools/.
    config = repo_root() / "tools" / "pyproject.toml"
    config_args = ["--config", str(config)] if config.is_file() else []

    commands: list[list[str]] = []
    lint_cmd = [sys.executable, "-m", "ruff", "check", *roots, *config_args]
    if fix:
        lint_cmd.append("--fix")
    commands.append(lint_cmd)

    if format_code:
        commands.append([sys.executable, "-m", "ruff", "format", *roots, *config_args])
    elif check_format:
        commands.append([sys.executable, "-m", "ruff", "format", "--check", *roots, *config_args])

    results: list[dict[str, Any]] = []
    ok = True
    for cmd in commands:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        results.append(
            {
                "command": cmd,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        if proc.returncode != 0:
            ok = False
        # Stream output for CLI usability
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)

    return {"ok": ok, "roots": roots, "results": results}
