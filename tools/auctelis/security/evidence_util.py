"""Build evidence records with commit, digest, and line provenance when available."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auctelis.security.models import AuthorityLayer, Evidence, EvidenceClass, VerificationStatus
from auctelis.supply_chain.digest import sha256_file
from auctelis.versioning import load_versions

# Multi-entry config types whose authority unit is a named record inside a file,
# not the whole file. Whole-file hashing makes every sibling reappear as "new"
# when one record changes.
_RECORD_DIGEST_TYPES = frozenset({"MCP Server Registration"})


@dataclass(slots=True)
class EvidenceContext:
    """Shared scan context for provenance-bound evidence construction."""

    repository_root: Path | None = None
    source_commit: str | None = None
    observed_at: str | None = None


def resolve_source_file(root: Path | None, repository_path: str | None) -> Path | None:
    if root is None or not repository_path:
        return None
    candidate = (root / repository_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def locate_needle_lines(text: str, needle: str | None) -> tuple[int | None, int | None]:
    """Return 1-indexed inclusive line span for the first needle match."""
    if not needle:
        return None, None
    lowered = text.lower()
    target = needle.lower()
    idx = lowered.find(target)
    if idx < 0:
        return None, None
    start_line = text.count("\n", 0, idx) + 1
    end_idx = idx + len(needle)
    end_line = text.count("\n", 0, end_idx) + 1
    return start_line, end_line


def _canonical_sha256(material: Any) -> str:
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def record_content_digest(component: dict[str, Any]) -> str | None:
    """Per-record digest for multi-entry authority surfaces (e.g. one MCP server)."""
    ctype = str(component.get("type") or "")
    if ctype not in _RECORD_DIGEST_TYPES:
        return None
    material = {
        "name": str(component.get("name") or ""),
        "command": component.get("command"),
        "args": list(component.get("args") or []),
        "url": component.get("url"),
        "declared_transport": component.get("declared_transport"),
        # Keys only — never hash secret values into identity material.
        "env_keys": list(component.get("env_keys") or []),
    }
    return f"sha256:{_canonical_sha256(material)}"


def component_content_digest(root: Path | None, component: dict[str, Any]) -> str | None:
    """Prefer per-record digest; fall back to whole-file hash for single-entry types."""
    record = record_content_digest(component)
    if record:
        return record
    path = resolve_source_file(root, component.get("repository_path"))
    if path is None:
        return None
    return f"sha256:{sha256_file(path)}"


def enrich_component_provenance(
    components: list[dict[str, Any]],
    *,
    root: Path | None,
) -> None:
    """Attach content digests used by fingerprints and evidence producers."""
    for component in components:
        digest = component_content_digest(root, component)
        if digest:
            component["content_digest"] = digest


def build_rule_evidence(
    evidences: list[Evidence],
    *,
    component: dict[str, Any],
    summary: str,
    ctx: EvidenceContext | None = None,
    status: VerificationStatus = "OBSERVED",
    evidence_class: EvidenceClass = "SOURCE_STATIC",
    limitations: list[str] | None = None,
    needle: str | None = None,
    collection_method: str = "deterministic_rule",
    authority_layer: AuthorityLayer = "CONFIGURED",
    derived_from: list[str] | None = None,
) -> Evidence:
    ctx = ctx or EvidenceContext()
    file_path = component.get("repository_path")
    line_start: int | None = None
    line_end: int | None = None
    content_digest = component.get("content_digest")
    source = resolve_source_file(ctx.repository_root, file_path)
    if source is not None:
        if not content_digest:
            content_digest = f"sha256:{sha256_file(source)}"
        if needle:
            try:
                text = source.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            line_start, line_end = locate_needle_lines(text, needle)

    versions = load_versions()
    eid = f"E-{len(evidences) + 1:03d}"
    ev = Evidence(
        evidence_id=eid,
        component_id=str(component.get("component_id") or "UNKNOWN"),
        evidence_class=evidence_class,
        verification_status=status,
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
        content_digest=content_digest,
        collection_method=collection_method,
        source_commit=ctx.source_commit,
        observed_at=ctx.observed_at,
        summary=summary,
        limitations=limitations
        or [
            "Static configuration observation only; host effective permissions not verified.",
            "CONFIGURED authority ≠ EFFECTIVE host permissions ≠ VERIFIED runtime behavior.",
        ],
        authority_layer=authority_layer,
        parser_version=str(component.get("adapter") or "inventory"),
        rule_pack_version=str(versions.get("rule_pack") or ""),
        derived_from=list(derived_from or []),
    )
    evidences.append(ev)
    return ev
