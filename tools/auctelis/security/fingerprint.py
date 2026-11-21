"""Stable component fingerprints for baseline identity (rename-resistant when content is hashed)."""

from __future__ import annotations

import hashlib
from typing import Any


def component_fingerprint(component: dict[str, Any]) -> str:
    """Return a short fingerprint preferring content digest over path.

    Identity priority:
    1. type + adapter + host + content_digest (stable across renames/moves of identical
       record bytes; host distinguishes the same config dropped under another host tree)
    2. type + adapter + host + name + repository_path (fallback when digest unavailable)

    For multi-entry files (MCP), ``content_digest`` is a per-record hash so sibling
    servers do not share identity. Identical records at two paths still share a
    fingerprint when host is equal (content clones); path is tracked separately.
    """
    ctype = str(component.get("type") or "").strip()
    adapter = str(component.get("adapter") or "").strip()
    digest = str(component.get("content_digest") or "").strip()
    name = str(component.get("name") or "").strip().lower()
    path = str(component.get("repository_path") or "").strip().replace("\\", "/")
    host = str(component.get("host_id") or "").strip().lower()

    if digest:
        material = f"{ctype}|{adapter}|{host}|{digest}"
    else:
        material = f"{ctype}|{adapter}|{host}|{name}|{path}"

    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def finding_key(
    rule_id: str, fingerprint: str | None = None, component_ids: list[str] | None = None
) -> str:
    """Stable finding identity for risk deltas.

    Prefer rule + content fingerprint so renames / component_id reshuffles do not
    look like new findings. Fall back to rule + component ids when no fingerprint.
    """
    if fingerprint:
        return f"{rule_id}:{fingerprint}"
    comps = ",".join(sorted(component_ids or []))
    return f"{rule_id}:{comps}"


def paths_by_fingerprint(components: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map fingerprint → sorted repository paths (supports content clones)."""
    mapping: dict[str, set[str]] = {}
    for component in components:
        fp = str(component.get("fingerprint") or component_fingerprint(component))
        path = str(component.get("repository_path") or component.get("name") or "").replace(
            "\\", "/"
        )
        mapping.setdefault(fp, set()).add(path)
    return {fp: sorted(paths) for fp, paths in sorted(mapping.items())}
