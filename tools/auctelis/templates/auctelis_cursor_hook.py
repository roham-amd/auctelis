#!/usr/bin/env python3
"""Cursor PreToolUse-style tripwire: AUTHORITY.lock on MCP and edits.

Install: ``auctelis hook install`` (writes ``~/.cursor/hooks.json``).
Requires: auctelis on PATH; a prior ``auctelis watch --seal`` (or ``lock``).

Cursor passes hook input as JSON on stdin and expects a JSON decision on stdout:

    {"permission": "allow" | "deny" | "ask", "user_message": "..."}

Behaviour:
1. ``beforeMCPExecution``: refuse a server name absent from the sealed lock.
   An empty MCP allowlist is deny-all (fail closed).
2. ``beforeShellExecution`` / ``beforeFileEdit``: refuse edits to
   authority-bearing paths — a human updates the lock.
3. Unknown events fail open; this is a tripwire, not a sandbox.
"""

from __future__ import annotations

import json
import os
import sys
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

_MCP_TOOL_HINTS = ("mcp__", "mcp_", "call_mcp", "mcp_server")


def _allow() -> int:
    print(json.dumps({"permission": "allow"}))
    return 0


def _deny(message: str) -> int:
    print(json.dumps({"permission": "deny", "user_message": message}))
    return 0


def _payload() -> dict:
    raw = os.environ.get("CURSOR_HOOK_INPUT") or ""
    if not raw and len(sys.argv) > 1:
        raw = sys.argv[1]
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    raw = raw.strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _event(payload: dict) -> str:
    return str(
        payload.get("hook_event_name") or payload.get("event") or payload.get("hook") or ""
    ).strip()


def _tool(payload: dict) -> str:
    return str(payload.get("tool_name") or payload.get("tool") or "").strip()


def _text(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for nested in ("file_path", "path", "command", "server"):
                inner = value.get(nested)
                if isinstance(inner, str) and inner.strip():
                    return inner.strip()
    return ""


def _target_path(payload: dict) -> str:
    return _text(payload, "file_path", "path", "tool_input", "arguments")


def _server_name(payload: dict) -> str | None:
    for key in ("server", "server_name", "mcp_server", "connector"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}
    if isinstance(tool_input, dict):
        for key in ("server", "server_name", "mcp_server"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    tool = _tool(payload)
    # Claude-style mcp__server__tool naming also appears in some bridges.
    if tool.lower().startswith("mcp__"):
        parts = tool.split("__")
        if len(parts) >= 2 and parts[1].strip():
            return parts[1].strip()
    parts = tool.replace("-", "_").split("__")
    for index, part in enumerate(parts):
        if part.lower() == "mcp" and index + 1 < len(parts) and parts[index + 1]:
            return parts[index + 1]
    if any(hint in tool.lower() for hint in _MCP_TOOL_HINTS):
        return tool
    return None


def _resolve_lock() -> tuple[Path, Path] | None:
    root = Path(
        os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ).resolve()
    lock = root / "AUTHORITY.lock"
    if lock.is_file():
        return lock, root
    home_lock = Path.home() / ".auctelis" / "AUTHORITY.lock"
    if home_lock.is_file():
        return home_lock, Path.home()
    return None


def _lock_server_names(lock_path: Path) -> set[str]:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    names: set[str] = set()
    for record in data.get("records") or []:
        if not isinstance(record, dict):
            continue
        kind = str(record.get("kind") or "").lower()
        if "mcp" not in kind and kind not in {"server", "mcp_server"}:
            continue
        for key in ("name", "id"):
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                names.add(value.strip().lower())
    for key in data.get("mcp_tools") or {}:
        names.add(str(key).strip().lower())
    return names


def _touches_authority(target: str, command: str) -> bool:
    blob = f"{target}\n{command}".replace("\\", "/")
    return any(marker in blob for marker in _AUTHORITY_MARKERS)


def main() -> int:
    payload = _payload()
    event = _event(payload).lower()
    tool = _tool(payload)
    target = _target_path(payload)

    is_mcp = event in {"beforemcpexecution"} or ("mcp" in event and "execution" in event)
    if is_mcp:
        server = _server_name(payload)
        if not server:
            return _deny(
                "auctelis: MCP call did not name a server — refused (fail closed). "
                "Human: reseal with `auctelis watch --seal` if this is intended."
            )
        resolved = _resolve_lock()
        if resolved is None:
            return _deny("auctelis: no AUTHORITY.lock — run `auctelis watch --seal` first.")
        lock, _root = resolved
        allowed = _lock_server_names(lock)
        if server.lower() not in allowed:
            return _deny(
                f"auctelis: MCP server `{server}` is not in AUTHORITY.lock — refused. "
                "Human: review with `auctelis watch`, then reseal yourself."
            )
        return _allow()

    if event in {"beforeshellexecution", "beforefileedit"}:
        command = _text(payload, "command", "tool_input", "arguments")
        if _touches_authority(target, command):
            return _deny(
                "auctelis: authority-bearing edit requires a human. "
                f"tool={tool or 'unknown'} path={target or '(command)'}. "
                "Human: review the change, then reseal AUTHORITY.lock yourself."
            )
        return _allow()

    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
