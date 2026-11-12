#!/usr/bin/env python3
"""Claude Code PreToolUse hook: hold agent edits to authority files.

Install: point PreToolUse at this script (or the thin .sh wrapper).
Requires: authdiff on PATH; a prior `authdiff lock` (repo) or `authdiff lock --home`.
Claude Code passes hook input as JSON on stdin (tool_name / tool_input.file_path).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_AUTHORITY_MARKERS = (
    "AUTHORITY.lock",
    ".authdiff.yml",
    ".authdiff.yaml",
    "/.mcp.json",
    "/mcp.json",
    "/hooks.json",
    "/SKILL.md",
    "/settings.json",
    "/settings.local.json",
    "/.claude/commands/",
)


def _parse_stdin(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if not raw:
        return "", ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        if raw.startswith("{"):
            return "", ""
        return "", raw
    if not isinstance(payload, dict):
        return "", ""
    tool = str(payload.get("tool_name") or "").strip()
    tool_input = payload.get("tool_input") or {}
    path = ""
    if isinstance(tool_input, dict):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()
    if not path:
        path = str(payload.get("file_path") or payload.get("path") or "").strip()
    return tool, path


def _touches_authority(path: str, raw: str, tool: str) -> bool:
    target = path.replace("\\", "/")
    if any(marker in target for marker in _AUTHORITY_MARKERS):
        return True
    if tool.lower() == "bash":
        blob = raw.replace("\\", "/")
        return any(marker.lstrip("/") in blob for marker in _AUTHORITY_MARKERS)
    return False


def main() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT") or ""
    if not raw and len(sys.argv) > 1:
        raw = sys.argv[1]
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()

    tool, target = _parse_stdin(raw)
    if tool.lower() in {"edit", "write"} and not target:
        print(
            f"authdiff: PreToolUse {tool} missing file_path — refusing (fail-closed).",
            file=sys.stderr,
        )
        return 2

    if not _touches_authority(target, raw, tool):
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    home = Path.home()
    lock = root / "AUTHORITY.lock"
    if not lock.is_file():
        home_lock = home / ".authdiff" / "AUTHORITY.lock"
        if home_lock.is_file():
            lock = home_lock
            root = home
        else:
            print(
                "authdiff: no AUTHORITY.lock — human must run: "
                "authdiff lock   or   authdiff lock --home",
                file=sys.stderr,
            )
            return 2

    if not shutil_which("authdiff"):
        print("authdiff: CLI not on PATH; install then re-run the edit.", file=sys.stderr)
        return 2

    with tempfile.NamedTemporaryFile(prefix="authdiff-hook-", delete=False) as tmp:
        hook_out = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["authdiff", "lock", "--check", "--lock-file", str(lock), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )
        hook_out.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        print("authdiff: authority-bearing path edit requires a human.", file=sys.stderr)
        print(f"  tool={tool or 'unknown'} path={target}", file=sys.stderr)
        if proc.returncode != 0:
            print("authdiff: existing authority drift detected:", file=sys.stderr)
            print(hook_out.read_text(encoding="utf-8")[:2000], file=sys.stderr)
        print(
            "Human: review the change, then update the lock yourself (do not ask the agent).",
            file=sys.stderr,
        )
        return 2
    finally:
        hook_out.unlink(missing_ok=True)


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
