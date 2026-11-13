#!/usr/bin/env python3
"""Claude Code PreToolUse hook: enforce AUTHORITY.lock on agent edits + MCP use.

Install: ``auctelis hook install`` (or point PreToolUse at this script).
Requires: auctelis on PATH; a prior ``auctelis lock`` (repo) or ``auctelis lock --home``.
Claude Code passes hook input as JSON on stdin (tool_name / tool_input.file_path).

Behaviour:
1. Edits to authority-bearing paths are refused (human must update the lock).
2. MCP / tool calls that reference a server name not present in the lock are refused.
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
    ".auctelis.yml",
    ".auctelis.yaml",
    "/.mcp.json",
    "/mcp.json",
    "/hooks.json",
    "/SKILL.md",
    "/settings.json",
    "/settings.local.json",
    "/.claude/commands/",
)

_MCP_TOOL_HINTS = (
    "mcp__",
    "mcp_",
    "listmcp",
    "call_mcp",
    "mcp_server",
)


def _parse_stdin(raw: str) -> tuple[str, str, dict]:
    raw = raw.strip()
    if not raw:
        return "", "", {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        if raw.startswith("{"):
            return "", "", {}
        return "", raw, {}
    if not isinstance(payload, dict):
        return "", "", {}
    tool = str(payload.get("tool_name") or "").strip()
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()
    if not path:
        path = str(payload.get("file_path") or payload.get("path") or "").strip()
    return tool, path, tool_input


def _touches_authority(path: str, raw: str, tool: str) -> bool:
    target = path.replace("\\", "/")
    if any(marker in target for marker in _AUTHORITY_MARKERS):
        return True
    if tool.lower() == "bash":
        blob = raw.replace("\\", "/")
        return any(marker.lstrip("/") in blob for marker in _AUTHORITY_MARKERS)
    return False


def _looks_like_mcp(tool: str, tool_input: dict, raw: str) -> str | None:
    """Return a candidate MCP server name if this tool call appears MCP-scoped."""
    t = tool.lower()
    for key in ("server", "server_name", "mcp_server", "name"):
        val = tool_input.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        if key in {"server", "server_name", "mcp_server"} or "mcp" in t:
            return val.strip()
    if any(h in t for h in _MCP_TOOL_HINTS):
        # mcp__server__tool convention
        parts = tool.replace("-", "_").split("_")
        for i, part in enumerate(parts):
            if part.lower() == "mcp" and i + 1 < len(parts) and parts[i + 1]:
                return parts[i + 1]
        return tool
    blob = raw.lower()
    if "mcp.json" in blob or "add-mcp" in blob or "mcp add" in blob:
        return "(mcp-config-change)"
    return None


def _lock_server_names(lock_path: Path) -> set[str]:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    names: set[str] = set()
    for rec in data.get("records") or []:
        if not isinstance(rec, dict):
            continue
        kind = str(rec.get("kind") or "").lower()
        if "mcp" not in kind and kind not in {"server", "mcp_server"}:
            continue
        for key in ("name", "id"):
            val = rec.get(key)
            if isinstance(val, str) and val.strip():
                names.add(val.strip().lower())
    for key in data.get("mcp_tools") or {}:
        names.add(str(key).strip().lower())
    return names


def _resolve_lock() -> tuple[Path, Path] | None:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    home = Path.home()
    lock = root / "AUTHORITY.lock"
    if lock.is_file():
        return lock, root
    home_lock = home / ".auctelis" / "AUTHORITY.lock"
    if home_lock.is_file():
        return home_lock, home
    return None


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def main() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT") or ""
    if not raw and len(sys.argv) > 1:
        raw = sys.argv[1]
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()

    tool, target, tool_input = _parse_stdin(raw)
    if tool.lower() in {"edit", "write"} and not target:
        print(
            f"auctelis: PreToolUse {tool} missing file_path — refusing (fail-closed).",
            file=sys.stderr,
        )
        return 2

    resolved = _resolve_lock()
    if resolved is None:
        if _touches_authority(target, raw, tool) or _looks_like_mcp(tool, tool_input, raw):
            print(
                "auctelis: no AUTHORITY.lock — human must run: "
                "auctelis lock   or   auctelis lock --home",
                file=sys.stderr,
            )
            return 2
        return 0

    lock, root = resolved

    # Lock-enforcing: refuse MCP servers not present in the sealed lock.
    # Fail closed when the lock has zero MCP records (empty allowlist ≠ allow-all).
    mcp_name = _looks_like_mcp(tool, tool_input, raw)
    if mcp_name and mcp_name != "(mcp-config-change)":
        allowed = _lock_server_names(lock)
        if mcp_name.lower() not in allowed:
            print(
                f"auctelis: MCP server `{mcp_name}` is not in AUTHORITY.lock — refused.",
                file=sys.stderr,
            )
            print(
                "Human: review with `auctelis vet` / `doctor --since-lock`, "
                "then reseal the lock yourself.",
                file=sys.stderr,
            )
            return 2

    if not _touches_authority(target, raw, tool) and mcp_name != "(mcp-config-change)":
        return 0

    if not shutil_which("auctelis"):
        print("auctelis: CLI not on PATH; install then re-run the edit.", file=sys.stderr)
        return 2

    with tempfile.NamedTemporaryFile(prefix="auctelis-hook-", delete=False) as tmp:
        hook_out = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["auctelis", "lock", "--check", "--lock-file", str(lock), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )
        hook_out.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        print("auctelis: authority-bearing path edit requires a human.", file=sys.stderr)
        print(f"  tool={tool or 'unknown'} path={target}", file=sys.stderr)
        if proc.returncode != 0:
            print("auctelis: existing authority drift detected:", file=sys.stderr)
            print(hook_out.read_text(encoding="utf-8")[:2000], file=sys.stderr)
        print(
            "Human: review the change, then update the lock yourself (do not ask the agent).",
            file=sys.stderr,
        )
        return 2
    finally:
        hook_out.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
