"""Per-project allow store — Project Trust consent for a cloned repo.

``auctelis allow`` records that a human reviewed the current project authority
hash. Session hooks and tripwires consult the store before treating project
MCP / settings as new reach.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auctelis.authority_card import screen_digest, sealable_records
from auctelis.authority_lock import build_authority_lock
from auctelis.host_scan import discover_project_surfaces, stage_project_surfaces
from auctelis.security.engine import run_security_scan

_STORE_NAME = "project-allow.json"


def allow_store_path(*, home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser() / ".auctelis" / _STORE_NAME


def project_key(root: Path) -> str:
    return str(root.expanduser().resolve())


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_allow_store(*, home: Path | None = None) -> dict[str, Any]:
    path = allow_store_path(home=home)
    if not path.is_file():
        return {"schema_version": "project-allow/1", "projects": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": "project-allow/1", "projects": {}}
    if not isinstance(data, dict):
        return {"schema_version": "project-allow/1", "projects": {}}
    projects = data.get("projects")
    if not isinstance(projects, dict):
        data["projects"] = {}
    data.setdefault("schema_version", "project-allow/1")
    return data


def save_allow_store(store: dict[str, Any], *, home: Path | None = None) -> Path:
    path = allow_store_path(home=home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def project_authority_hash(
    root: Path,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Return ``(digest, sealable_records, surface_paths)`` for a project tree."""
    from contextlib import ExitStack

    root = root.expanduser().resolve()
    surfaces = [s for s in discover_project_surfaces(root=root) if s.exists]
    if not surfaces:
        empty = hashlib.sha256(b"empty-project").hexdigest()[:12]
        return empty, [], []
    with ExitStack() as stack:
        synth, _present = stage_project_surfaces(stack, root=root)
        scan = run_security_scan(synth)
        lock = build_authority_lock(synth, scan=scan)
    sealable = sealable_records(list(lock.get("records") or []))
    digest = screen_digest(sealable)
    paths = [str(s.path) for s in surfaces]
    return digest, sealable, paths


def allow_project(
    root: Path | None = None,
    *,
    home: Path | None = None,
    accept: str | None = None,
) -> dict[str, Any]:
    """Record human consent for the current project authority hash.

    Requires ``--accept <digest>`` whenever the project has sealable records,
    matching ``watch --seal --accept`` consent integrity.
    """
    project = (root or Path.cwd()).expanduser().resolve()
    digest, sealable, paths = project_authority_hash(project)
    expected = str(accept or "").strip().lower()
    if sealable and not expected:
        raise ValueError(f"allow requires --accept {digest} (digest of current project authority)")
    if expected and expected != digest:
        raise ValueError(f"accept digest mismatch: got {expected!r}, project screen is {digest!r}")
    store = load_allow_store(home=home)
    projects = store.setdefault("projects", {})
    entry = {
        "path": str(project),
        "digest": digest,
        "allowed_at": _now_iso(),
        "record_count": len(sealable),
        "surfaces": paths,
    }
    projects[project_key(project)] = entry
    save_allow_store(store, home=home)
    return entry


def project_is_allowed(
    root: Path | None = None,
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    """Return allow status for a project (allowed / drifted / unknown)."""
    project = (root or Path.cwd()).expanduser().resolve()
    digest, sealable, paths = project_authority_hash(project)
    store = load_allow_store(home=home)
    entry = (store.get("projects") or {}).get(project_key(project))
    if not entry:
        return {
            "status": "unknown",
            "digest": digest,
            "record_count": len(sealable),
            "surfaces": paths,
            "allowed": False,
        }
    prior = str(entry.get("digest") or "")
    if prior == digest:
        return {
            "status": "allowed",
            "digest": digest,
            "record_count": len(sealable),
            "surfaces": paths,
            "allowed": True,
            "allowed_at": entry.get("allowed_at"),
        }
    return {
        "status": "drifted",
        "digest": digest,
        "prior_digest": prior,
        "record_count": len(sealable),
        "surfaces": paths,
        "allowed": False,
        "allowed_at": entry.get("allowed_at"),
    }
