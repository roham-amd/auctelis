"""Baseline save / load / risk-aware diff for recurring auctelis assessments."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auctelis.jsonio import read_json, write_json
from auctelis.security.engine import ScanResult
from auctelis.security.fingerprint import (
    component_fingerprint,
    finding_key,
    paths_by_fingerprint,
)

BASELINE_VERSION = "1.3"


def _finding_identity(finding: Any, inventory: dict[str, Any]) -> str:
    comps_by_id = {str(c.get("component_id") or ""): c for c in inventory.get("components") or []}
    fingerprints: list[str] = []
    for cid in finding.component_ids:
        comp = comps_by_id.get(cid)
        if comp:
            fingerprints.append(str(comp.get("fingerprint") or component_fingerprint(comp)))
    fp = fingerprints[0] if fingerprints else None
    return finding_key(finding.rule_id, fingerprint=fp, component_ids=finding.component_ids)


def _fingerprint_by_path(path_map: dict[str, list[str]]) -> dict[str, str]:
    """Invert fingerprint→paths to path→fingerprint (last write wins if clash)."""
    out: dict[str, str] = {}
    for fp, paths in path_map.items():
        for path in paths:
            out[str(path)] = str(fp)
    return out


def save_baseline(scan: ScanResult, path: Path) -> dict[str, Any]:
    components = list(scan.inventory.get("components") or [])
    path_map = paths_by_fingerprint(components)
    by_path = _fingerprint_by_path(path_map)
    doc = {
        "baseline_version": BASELINE_VERSION,
        "saved_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "product": "auctelis",
        "product_version": scan.product_version,
        "repository": scan.repository_path,
        "audited_commit": scan.commit,
        "component_fingerprints": sorted(path_map.keys()),
        "component_paths_by_fingerprint": path_map,
        "fingerprint_by_path": by_path,
        # Legacy path-tied keys retained for older consumers; gate logic prefers fingerprints.
        "component_keys": sorted(
            {
                f"{c.get('fingerprint') or component_fingerprint(c)}:"
                f"{(c.get('repository_path') or c.get('name') or '')}"
                for c in components
            }
        ),
        "finding_keys": sorted({_finding_identity(f, scan.inventory) for f in scan.findings}),
        "findings": [f.to_dict() for f in scan.findings],
        "summary": scan.to_findings_doc()["summary"],
        "limitations": [
            "Fingerprints prefer content digest over path; renames/moves of identical bytes stay stable.",
            "Same-path content changes are modifications (not unrelated remove+add).",
            "Content clones share a fingerprint; paths_by_fingerprint lists all locations.",
            "Risk delta is deterministic-rule based; AI semantic findings are not included.",
        ],
    }
    write_json(path, doc)
    return doc


def load_baseline(path: Path) -> dict[str, Any]:
    doc = read_json(path)
    if not isinstance(doc, dict):
        raise TypeError(f"baseline must be a JSON object: {path}")
    return doc


def _moved_components(
    base_paths: dict[str, list[str]],
    current_paths: dict[str, list[str]],
) -> list[dict[str, Any]]:
    moved: list[dict[str, Any]] = []
    for fp in sorted(set(base_paths) & set(current_paths)):
        before = set(base_paths.get(fp) or [])
        after = set(current_paths.get(fp) or [])
        if before != after:
            moved.append(
                {
                    "fingerprint": fp,
                    "paths_before": sorted(before),
                    "paths_after": sorted(after),
                    "kind": "clone_or_relocate"
                    if before & after or (not before - after and after - before)
                    else "relocate",
                }
            )
    return moved


def _modified_components(
    base_by_path: dict[str, str],
    current_by_path: dict[str, str],
) -> list[dict[str, Any]]:
    """Same repository path, different content fingerprint ⇒ modification."""
    modified: list[dict[str, Any]] = []
    for path in sorted(set(base_by_path) & set(current_by_path)):
        before = base_by_path[path]
        after = current_by_path[path]
        if before != after:
            modified.append(
                {
                    "path": path,
                    "fingerprint_before": before,
                    "fingerprint_after": after,
                    "kind": "content_modification",
                }
            )
    return modified


def _reconstruct_path_maps(baseline: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, str]]:
    base_paths = dict(baseline.get("component_paths_by_fingerprint") or {})
    base_by_path = dict(baseline.get("fingerprint_by_path") or {})
    if not base_paths:
        for key in baseline.get("component_keys") or []:
            if ":" in str(key):
                fp, _, path = str(key).partition(":")
                base_paths.setdefault(fp, [])
                if path and path not in base_paths[fp]:
                    base_paths[fp].append(path)
        for fp in baseline.get("component_fingerprints") or []:
            base_paths.setdefault(str(fp), base_paths.get(str(fp), []))
    if not base_by_path:
        base_by_path = _fingerprint_by_path(base_paths)
    return base_paths, base_by_path


def diff_against_baseline(scan: ScanResult, baseline: dict[str, Any]) -> dict[str, Any]:
    components = list(scan.inventory.get("components") or [])
    current_paths = paths_by_fingerprint(components)
    current_by_path = _fingerprint_by_path(current_paths)
    base_paths, base_by_path = _reconstruct_path_maps(baseline)

    modified = _modified_components(base_by_path, current_by_path)
    modified_before = {m["fingerprint_before"] for m in modified}
    modified_after = {m["fingerprint_after"] for m in modified}

    current_fps = set(current_paths)
    base_fps = set(base_paths)
    # Fingerprints that only appear because of same-path content edits are modifications,
    # not unrelated additions/removals.
    raw_added = current_fps - base_fps
    raw_removed = base_fps - current_fps
    added_fps = sorted(raw_added - modified_after)
    removed_fps = sorted(raw_removed - modified_before)
    moved = _moved_components(base_paths, current_paths)

    current_findings = {_finding_identity(f, scan.inventory) for f in scan.findings}
    base_findings = set(baseline.get("finding_keys") or [])
    normalized_base: set[str] = set()
    for key in base_findings:
        parts = str(key).split(":")
        if (
            len(parts) >= 2
            and len(parts[1]) == 16
            and all(c in "0123456789abcdef" for c in parts[1])
        ):
            normalized_base.add(f"{parts[0]}:{parts[1]}")
        else:
            normalized_base.add(str(key))
    added_findings = sorted(current_findings - normalized_base)
    removed_findings = sorted(normalized_base - current_findings)

    from auctelis.security.gating import is_gate_finding, is_high_gate_finding

    added_set = set(added_findings)
    high_new = [
        f.to_dict()
        for f in scan.findings
        if _finding_identity(f, scan.inventory) in added_set and is_high_gate_finding(f)
    ]
    gated_new = [
        f.to_dict()
        for f in scan.findings
        if _finding_identity(f, scan.inventory) in added_set and is_gate_finding(f)
    ]

    return {
        "diff_version": "1.3",
        "kind": "auctelis_guard_risk_delta",
        "base": {
            "saved_at_utc": baseline.get("saved_at_utc"),
            "audited_commit": baseline.get("audited_commit"),
            "baseline_version": baseline.get("baseline_version"),
        },
        "target": {
            "audited_commit": scan.commit,
            "collected_at_utc": scan.collected_at_utc,
        },
        "summary": {
            "fingerprints_added": len(added_fps),
            "fingerprints_removed": len(removed_fps),
            "components_moved": len(moved),
            "components_modified": len(modified),
            "findings_added": len(added_findings),
            "findings_removed": len(removed_findings),
            "gated_findings_added": len(gated_new),
            "high_or_critical_findings_added": len(high_new),
            "path_keys_added": len(
                {
                    f"{c.get('fingerprint') or component_fingerprint(c)}:"
                    f"{(c.get('repository_path') or '')}"
                    for c in components
                }
                - set(baseline.get("component_keys") or [])
            ),
        },
        "changes": {
            "fingerprints_added": added_fps,
            "fingerprints_removed": removed_fps,
            "components_moved": moved,
            "components_modified": modified,
            "findings_added": added_findings,
            "findings_removed": removed_findings,
            "high_or_critical_new_findings": high_new,
            "gated_new_findings": gated_new,
        },
        "policy_hints": {
            "block_if_high_or_critical_added": len(high_new) > 0,
            "incomplete_coverage": bool(scan.coverage.get("not_verified")),
            "rename_or_move_only": bool(moved)
            and not added_fps
            and not removed_fps
            and not modified
            and not added_findings,
            "content_modification_only": bool(modified)
            and not added_fps
            and not removed_fps
            and not moved,
        },
        "limitations": [
            "Risk delta is deterministic-rule based; AI semantic findings are not included.",
            "CAPABILITY-class observations do not count as high/critical gate failures.",
            "Fingerprint-stable path changes are moves; same-path digest changes are modifications.",
        ],
    }
