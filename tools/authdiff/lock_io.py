"""AUTHORITY.lock file I/O (no scanner dependency).

JSON is the canonical on-disk format. A tiny YAML subset remains for legacy
``mcp_tools`` pins used by the broker MVP.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _loads_object(text: str) -> dict[str, Any]:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("AUTHORITY lock root must be a JSON object")
    return data


def _parse_simple_lock_yaml(text: str) -> dict[str, Any]:
    """Parse a tiny AUTHORITY.lock subset without a YAML dependency."""
    tools: dict[str, str] = {}
    in_tools = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in {"mcp_tools:", "mcp_tools: {}"}:
            in_tools = True
            continue
        if in_tools and line.startswith("  ") and ":" in line:
            key, _, val = stripped.partition(":")
            tools[key.strip()] = val.strip().strip("\"'")
        elif in_tools and not line.startswith((" ", "\t")):
            in_tools = False
    return {"mcp_tools": tools, "version": 1}


def load_authority_lock(path: Path) -> dict[str, Any]:
    """Load AUTHORITY.lock (JSON preferred; tiny YAML subset for legacy)."""
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".json" or name.endswith(".lock.json"):
        return _loads_object(text)
    if suffix in {".yml", ".yaml"} or "lock" in name:
        try:
            return _loads_object(text)
        except (json.JSONDecodeError, ValueError):
            return _parse_simple_lock_yaml(text)
    return _loads_object(text)
