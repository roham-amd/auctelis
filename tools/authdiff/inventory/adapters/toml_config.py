"""Bounded TOML reader for Codex / other host configs (no third-party TOML dep).

Supports a minimal subset sufficient for ``[mcp_servers.*]`` / ``[mcp.servers.*]``
tables with string and boolean values. Unknown syntax is recorded as
``unparsed_agent_config`` (fail closed).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from authdiff.inventory.io import safe_read_text, select_files
from authdiff.inventory.limits import CollectorLimits

_TABLE_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_KV_RE = re.compile(
    r'^([A-Za-z0-9_.-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(true|false)|([0-9]+))\s*$',
    re.IGNORECASE,
)


def _parse_simple_toml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        table = _TABLE_RE.match(line.strip())
        if table:
            current = [p.strip() for p in table.group(1).split(".")]
            cursor: dict[str, Any] = root
            for part in current:
                cursor = cursor.setdefault(part, {})
            continue
        kv = _KV_RE.match(line.strip())
        if not kv:
            raise ValueError(f"Unsupported TOML line: {line.strip()[:80]}")
        key = kv.group(1)
        if kv.group(2) is not None:
            value: Any = kv.group(2)
        elif kv.group(3) is not None:
            value = kv.group(3)
        elif kv.group(4) is not None:
            value = kv.group(4).lower() == "true"
        else:
            value = int(kv.group(5))
        cursor = root
        for part in current:
            cursor = cursor.setdefault(part, {})
        if not isinstance(cursor, dict):
            raise ValueError(f"Cannot assign under non-table at {'.'.join(current)}")
        cursor[key] = value
    return root


def _iter_mcp_servers(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for key in ("mcp_servers", "mcpServers"):
        block = data.get(key)
        if isinstance(block, dict):
            for name, cfg in block.items():
                if isinstance(cfg, dict):
                    out.append((str(name), cfg))
    mcp = data.get("mcp")
    if isinstance(mcp, dict) and isinstance(mcp.get("servers"), dict):
        for name, cfg in mcp["servers"].items():
            if isinstance(cfg, dict):
                out.append((str(name), cfg))
    return out


def discover_toml_mcp_configs(
    root: Path,
    *,
    files: list[Path],
    limits: CollectorLimits,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in select_files(
        files,
        lambda p: (
            p.name.lower() in {"config.toml", "mcp.toml", "codex.toml"}
            or (p.suffix.lower() == ".toml" and "mcp" in p.name.lower())
        ),
    ):
        raw = safe_read_text(path, root=root, limits=limits, events=events, adapter="toml_mcp")
        rel = path.relative_to(root).as_posix()
        if raw is None:
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "toml_mcp",
                    "path": rel,
                    "message": "unreadable or oversize TOML agent config",
                }
            )
            continue
        try:
            data = _parse_simple_toml(raw)
        except ValueError as exc:
            events.append(
                {
                    "type": "unparsed_agent_config",
                    "adapter": "toml_mcp",
                    "path": rel,
                    "message": str(exc),
                }
            )
            continue
        for name, cfg in _iter_mcp_servers(data):
            hints: list[str] = []
            command = str(cfg.get("command") or "")
            raw_args = cfg.get("args")
            args: list[Any] = list(raw_args) if isinstance(raw_args, list) else []
            if command:
                hints.append("local_command_transport")
            if cfg.get("url"):
                hints.append("remote_endpoint")
            env = cfg.get("env") or cfg.get("environment")
            if isinstance(env, dict) and env:
                hints.append("sets_environment")
            results.append(
                {
                    "name": name,
                    "type": "MCP Server Registration",
                    "reference_kind": "LOCAL_CONFIGURATION_OR_INSTRUCTIONS",
                    "repository_path": rel,
                    "adapter": "toml_mcp",
                    "adapter_maturity": "PARTIAL",
                    "discovery_status": "IDENTIFIED",
                    "command": command or None,
                    "args": args,
                    "url": cfg.get("url"),
                    "host_id": "codex",
                    "priority_hints": hints,
                }
            )
    return results
