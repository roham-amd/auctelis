"""TOML reader for Codex / other host configs via stdlib ``tomllib``.

Full TOML 1.0 (inline arrays, nested tables). Parse failures are recorded as
``unparsed_agent_config`` (fail closed).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from auctelis.inventory.adapters.mcp import build_mcp_server_entry
from auctelis.inventory.io import safe_read_text, select_files
from auctelis.inventory.limits import CollectorLimits

_AGENT_TOML_DIRS = frozenset({".codex", ".cursor", ".claude", ".gemini", ".opencode"})


def _parse_simple_toml(text: str) -> dict[str, Any]:
    """Parse TOML text; raise ``ValueError`` on syntax errors (fail closed)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("TOML root must be a table")
    return data


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

    def _toml_mcp_candidate(path: Path) -> bool:
        name = path.name.lower()
        parts = {part.lower() for part in path.parts}
        if name in {"mcp.toml", "codex.toml"}:
            return True
        if name.endswith(".toml") and "mcp" in name:
            return True
        return bool(name == "config.toml" and (parts & _AGENT_TOML_DIRS))

    for path in select_files(files, _toml_mcp_candidate):
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
            results.append(
                build_mcp_server_entry(
                    name=name,
                    cfg=cfg,
                    rel=rel,
                    adapter="toml_mcp",
                    default_host_id="codex",
                )
            )
    return results
