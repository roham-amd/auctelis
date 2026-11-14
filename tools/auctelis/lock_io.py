"""AUTHORITY.lock file I/O (no scanner dependency).

JSON is the canonical on-disk format. A tiny YAML subset remains for legacy
``mcp_tools`` pins used by the broker MVP. Every JSON lock is schema-validated
on load (fail closed on hollow / malformed documents).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class AuthorityLockError(ValueError):
    """Raised when an AUTHORITY.lock fails schema or hollowness checks."""


def _loads_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuthorityLockError(f"AUTHORITY lock is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AuthorityLockError("AUTHORITY lock root must be a JSON object")
    return data


def _parse_simple_lock_yaml(text: str) -> dict[str, Any]:
    """Parse a tiny AUTHORITY.lock subset without a YAML dependency."""
    tools: dict[str, str] = {}
    in_tools = False
    found_tools = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in {"mcp_tools:", "mcp_tools: {}"}:
            in_tools = True
            found_tools = True
            continue
        if in_tools and line.startswith("  ") and ":" in line:
            key, _, val = stripped.partition(":")
            tools[key.strip()] = val.strip().strip("\"'")
        elif in_tools and not line.startswith((" ", "\t")):
            in_tools = False
    if not found_tools:
        raise AuthorityLockError("AUTHORITY.lock is neither valid JSON nor a YAML mcp_tools lock")
    return {"mcp_tools": tools, "version": 1}


@lru_cache(maxsize=1)
def _lock_schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "data" / "authority-lock.schema.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"authority-lock schema must be an object: {path}")
    return data


def validate_authority_lock(data: dict[str, Any], *, path: Path | None = None) -> None:
    """Fail closed on schema violations and hollow locks (no records, no tools)."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise AuthorityLockError("jsonschema is required to validate AUTHORITY.lock") from exc
    try:
        jsonschema.validate(instance=data, schema=_lock_schema())
    except jsonschema.ValidationError as exc:
        where = f" ({path})" if path else ""
        raise AuthorityLockError(f"AUTHORITY.lock schema invalid{where}: {exc.message}") from exc

    records = data.get("records")
    tools = data.get("mcp_tools") or {}
    # Legacy YAML mcp_tools-only locks are allowed for broker pins.
    if records is None and tools:
        return
    if records is not None and not isinstance(records, list):
        raise AuthorityLockError("AUTHORITY.lock records must be an array")
    # Full JSON locks must include records[] (may be empty for a clean tree).
    if "mcp_tools" not in data and records is None:
        raise AuthorityLockError("AUTHORITY.lock missing records[]")


def load_authority_lock(path: Path) -> dict[str, Any]:
    """Load AUTHORITY.lock (JSON preferred; tiny YAML subset for legacy)."""
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".json" or name.endswith(".lock.json"):
        data = _loads_object(text)
        validate_authority_lock(data, path=path)
        return data
    if suffix in {".yml", ".yaml"} or "lock" in name:
        # A document that starts with `{` is JSON: never fall back to YAML on a
        # truncated/merge-conflicted file (that would silently become an empty lock).
        if text.lstrip().startswith("{"):
            data = _loads_object(text)
            validate_authority_lock(data, path=path)
            return data
        return _parse_simple_lock_yaml(text)
    data = _loads_object(text)
    validate_authority_lock(data, path=path)
    return data
