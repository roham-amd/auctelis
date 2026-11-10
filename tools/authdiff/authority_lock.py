"""Committed AUTHORITY.lock — record-level authority identity for PR review.

``authdiff lock`` writes a sorted canonical lock. ``lock --check`` / ``scan --locked``
regenerates and compares. CODEOWNERS on this file is the intended approval path.

Diff semantics (product contract):
- Match records by ``identity_key`` (host|kind|name), not incidental file path.
- Classify each delta as addition / expansion / reduction / replacement /
  representation / mixed.
- New identities are additions; capability growth on an existing identity is
  expansion. Path or digest-only churn is representation, not new authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from authdiff.lock_io import load_authority_lock
from authdiff.security.authority import (
    build_authority_snapshot,
    logical_authority_id,
)
from authdiff.security.engine import ScanResult, run_security_scan
from authdiff.versioning import product_version

# Re-export for callers that historically imported from authority_lock / broker.
__all__ = [
    "LOCK_NAME",
    "LOCK_VERSION",
    "build_approval_record",
    "build_authority_lock",
    "check_locked",
    "classify_record_change",
    "default_lock_path",
    "diff_authority_locks",
    "identity_key",
    "load_authority_lock",
    "normalize_lock_for_compare",
    "render_lock_diff_lines",
    "run_lock_command",
    "write_authority_lock",
]

LOCK_NAME = "AUTHORITY.lock"
LOCK_VERSION = 1

ChangeClass = Literal[
    "addition",
    "expansion",
    "reduction",
    "replacement",
    "representation",
    "mixed",
]

_PIN_RANK = {
    "digest": 0,
    "pinned": 1,
    "n/a": 2,
    "unknown": 3,
    "floating": 4,
}
_APPROVAL_RANK = {
    "prompt": 0,
    "unknown": 1,
    "auto": 2,
    "bypass": 3,
}
_AUTHORITY_FIELDS = (
    "capabilities",
    "destinations",
    "env_keys",
    "pin_state",
    "approval_posture",
)
_REPRESENTATION_FIELDS = ("path", "digest", "fingerprint")


def default_lock_path(root: Path) -> Path:
    return root.resolve() / LOCK_NAME


def build_approval_record(
    *,
    owner: str,
    lock_hash: str,
    audited_commit: str | None,
    policy_hash: str | None,
    justification: str = "Authority state accepted after human review",
    exceptions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind a human decision to the exact lock / commit / policy state."""
    return {
        "owner": owner.strip(),
        "approved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lock_hash": lock_hash,
        "audited_commit": audited_commit,
        "policy_hash": policy_hash,
        "justification": justification.strip() or "Authority state accepted after human review",
        "exceptions": list(exceptions or []),
    }


def identity_key(record: dict[str, Any]) -> str:
    """Stable authority identity independent of incidental file location."""
    explicit = record.get("identity_key")
    if explicit:
        return str(explicit)
    host = str(record.get("host") or "").strip().lower()
    kind = str(record.get("kind") or "").strip().lower()
    name = str(record.get("name") or "").strip().lower()
    if host or kind or name:
        return f"{host}|{kind}|{name}"
    return str(record.get("id") or "")


def _policy_hash(root: Path) -> str | None:
    for name in (".authdiff.yml", ".authdiff.yaml"):
        path = root / name
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return f"sha256:{digest}"
    return None


def _record_from_component(
    comp: dict[str, Any], raw: dict[str, Any] | None = None
) -> dict[str, Any]:
    raw = raw or {}
    host = str(comp.get("host") or "")
    kind = str(comp.get("kind") or "")
    name = str(comp.get("name") or "")
    path = str(comp.get("path") or "").replace("\\", "/")
    logical = logical_authority_id(
        {
            "host": host,
            "kind": kind,
            "name": name,
            "path": path,
            "id": comp.get("id"),
        }
    )
    key = identity_key({"host": host, "kind": kind, "name": name})
    return {
        "id": logical,
        "identity_key": key,
        "host": host,
        "kind": kind,
        "name": name,
        "path": path,
        "digest": str(raw.get("content_digest") or ""),
        "fingerprint": str(comp.get("fingerprint") or ""),
        "pin_state": str(comp.get("pin_state") or "unknown"),
        "approval_posture": str(comp.get("approval_posture") or "unknown"),
        "capabilities": list(comp.get("capabilities") or []),
        "destinations": list(comp.get("destinations") or []),
        "env_keys": list(raw.get("env_keys") or []),
    }


def build_authority_lock(root: Path, *, scan: ScanResult | None = None) -> dict[str, Any]:
    """Return a canonical AUTHORITY.lock document for ``root``.

    Pass an existing ``ScanResult`` (e.g. from ``scan --locked``) to avoid a
    second full security scan of the same tree.
    """
    root = root.resolve()
    if scan is None:
        scan = run_security_scan(root)
    snapshot = build_authority_snapshot(scan)
    by_fp = {
        str(c.get("fingerprint") or ""): c
        for c in (scan.inventory.get("components") or [])
        if isinstance(c, dict)
    }
    records: list[dict[str, Any]] = []
    for comp in snapshot.get("components") or []:
        if not isinstance(comp, dict):
            continue
        raw = by_fp.get(str(comp.get("fingerprint") or ""), {})
        records.append(_record_from_component(comp, raw))
    records.sort(key=lambda r: (r["kind"], r["path"], r["name"], r["id"]))

    body: dict[str, Any] = {
        "version": LOCK_VERSION,
        "product": "authdiff",
        "product_version": product_version(),
        "policy_hash": _policy_hash(root),
        "records": records,
        # Broker / snapshot compatibility (tool pins filled by `snapshot`).
        "mcp_tools": {},
        "mcp_servers": {
            r["name"] or r["id"]: {
                "path": r["path"],
                "digest": r["digest"],
                "pin_state": r["pin_state"],
                "allowed": True,
            }
            for r in records
            if r["kind"] == "MCP Server Registration"
        },
    }
    # Seal authority state only. Absolute `repository` path and `audited_commit`
    # are volatile across clones / no-op re-locks and must not churn lock_hash
    # (merge conflicts on hash alone with identical records).
    _SEAL_EXCLUDE = {"lock_hash", "repository", "audited_commit", "approvals", "approved_findings"}
    canonical = json.dumps(
        {k: v for k, v in body.items() if k not in _SEAL_EXCLUDE},
        sort_keys=True,
        separators=(",", ":"),
    )
    body["lock_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    # Non-sealed metadata for humans / tooling (ignored by normalize_lock_for_compare).
    body["audited_commit"] = scan.commit
    # Preserve prior human approvals / accepted findings across regenerations.
    body["approvals"] = []
    body["approved_findings"] = []
    existing_path = default_lock_path(root)
    if existing_path.is_file():
        try:
            prior = load_authority_lock(existing_path)
            body["approvals"] = list(prior.get("approvals") or [])
            body["approved_findings"] = list(prior.get("approved_findings") or [])
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return body


def _gated_lock_blockers(scan: ScanResult) -> list[str]:
    """HIGH/CRITICAL gate findings that must not be silently blessed into a lock."""
    from authdiff.security.gating import is_high_gate_finding

    blockers: list[str] = []
    for finding in scan.findings:
        if not is_high_gate_finding(finding):
            continue
        blockers.append(f"{finding.rule_id} [{finding.severity}] {finding.title}")
    return blockers


def write_authority_lock(
    root: Path,
    *,
    path: Path | None = None,
    approval_owner: str | None = None,
    accept_gated: bool = False,
    scan: ScanResult | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    if scan is None:
        scan = run_security_scan(root)
    blockers = _gated_lock_blockers(scan)
    if blockers and not accept_gated:
        preview = "; ".join(blockers[:3])
        more = f" (+{len(blockers) - 3} more)" if len(blockers) > 3 else ""
        raise ValueError(
            "refusing to lock a tree with high/critical gated findings without "
            f"--accept-gated. Seen: {preview}{more}"
        )
    lock = build_authority_lock(root, scan=scan)
    if approval_owner and approval_owner.strip():
        # Approvals bind to the sealed authority hash; they are not part of it.
        record = build_approval_record(
            owner=approval_owner,
            lock_hash=str(lock.get("lock_hash") or ""),
            audited_commit=lock.get("audited_commit"),
            policy_hash=lock.get("policy_hash"),
        )
        lock["approvals"] = [*list(lock.get("approvals") or []), record]
    dest = path or default_lock_path(root)
    dest.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest, lock


def normalize_lock_for_compare(lock: dict[str, Any]) -> dict[str, Any]:
    """Strip ephemeral fields so regenerate-vs-disk compares are stable."""
    records = []
    for rec in lock.get("records") or []:
        if not isinstance(rec, dict):
            continue
        normalized = {
            "id": rec.get("id"),
            "identity_key": identity_key(rec),
            "host": rec.get("host"),
            "kind": rec.get("kind"),
            "name": rec.get("name"),
            "path": rec.get("path"),
            "digest": rec.get("digest"),
            "fingerprint": rec.get("fingerprint"),
            "pin_state": rec.get("pin_state"),
            "approval_posture": rec.get("approval_posture"),
            "capabilities": sorted(str(c) for c in (rec.get("capabilities") or [])),
            "destinations": sorted(str(d) for d in (rec.get("destinations") or [])),
            "env_keys": sorted(str(k) for k in (rec.get("env_keys") or [])),
        }
        records.append(normalized)
    records.sort(
        key=lambda r: (
            r.get("identity_key") or "",
            r.get("kind") or "",
            r.get("path") or "",
            r.get("name") or "",
            r.get("id") or "",
        )
    )
    return {
        "version": int(lock.get("version") or 1),
        "policy_hash": lock.get("policy_hash"),
        "records": records,
        "mcp_tools": lock.get("mcp_tools") or {},
    }


def _index_by_identity(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map identity_key → record; fall back to id when keys collide."""
    out: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = identity_key(rec)
        if not key:
            key = str(rec.get("id") or "")
        if key in out:
            # Collision: keep both addressable via path-qualified id.
            key = str(rec.get("id") or key)
        if key:
            out[key] = rec
    return out


def _set_delta(before: list[str], after: list[str]) -> tuple[bool, bool]:
    b, a = set(before), set(after)
    return bool(a - b), bool(b - a)


def classify_record_change(
    before: dict[str, Any],
    after: dict[str, Any],
) -> ChangeClass:
    """Classify how one matched record changed between locks."""
    grew = False
    shrank = False
    authority_touched = False
    representation_only = True

    for field in _AUTHORITY_FIELDS:
        b_val, a_val = before.get(field), after.get(field)
        if b_val == a_val:
            continue
        authority_touched = True
        representation_only = False
        if field in {"capabilities", "destinations", "env_keys"}:
            up, down = _set_delta(
                [str(x) for x in (b_val or [])],
                [str(x) for x in (a_val or [])],
            )
            grew = grew or up
            shrank = shrank or down
        elif field == "pin_state":
            b_rank = _PIN_RANK.get(str(b_val or "unknown"), 3)
            a_rank = _PIN_RANK.get(str(a_val or "unknown"), 3)
            grew = grew or a_rank > b_rank
            shrank = shrank or a_rank < b_rank
        elif field == "approval_posture":
            b_rank = _APPROVAL_RANK.get(str(b_val or "unknown"), 1)
            a_rank = _APPROVAL_RANK.get(str(a_val or "unknown"), 1)
            grew = grew or a_rank > b_rank
            shrank = shrank or a_rank < b_rank

    for field in _REPRESENTATION_FIELDS:
        if before.get(field) != after.get(field):
            # Path/digest/fingerprint churn alone is representation.
            pass

    if not authority_touched:
        # Name/host/kind identity is fixed by matching key; leftover diffs are packaging.
        if any(before.get(f) != after.get(f) for f in (*_REPRESENTATION_FIELDS, "id")):
            return "representation"
        return "representation"

    if grew and shrank:
        return "mixed"
    if grew:
        return "expansion"
    if shrank:
        return "reduction"
    # Authority field changed without clear grow/shrink (e.g. equal-size set rewrite).
    if representation_only:
        return "representation"
    return "replacement"


def diff_authority_locks(
    base: dict[str, Any],
    head: dict[str, Any],
) -> dict[str, Any]:
    """Record-level authority diff with expansion/reduction classification."""
    base_n = normalize_lock_for_compare(base)
    head_n = normalize_lock_for_compare(head)
    base_by = _index_by_identity(base_n["records"])
    head_by = _index_by_identity(head_n["records"])

    added = [
        {**head_by[i], "change_class": "addition"} for i in sorted(set(head_by) - set(base_by))
    ]
    removed = [
        {**base_by[i], "change_class": "reduction"} for i in sorted(set(base_by) - set(head_by))
    ]
    changed: list[dict[str, Any]] = []
    for key in sorted(set(base_by) & set(head_by)):
        before, after = base_by[key], head_by[key]
        # Compare without ephemeral compare helpers.
        before_cmp = {k: v for k, v in before.items() if k != "change_class"}
        after_cmp = {k: v for k, v in after.items() if k != "change_class"}
        if before_cmp == after_cmp:
            continue
        change_class = classify_record_change(before_cmp, after_cmp)
        changed.append(
            {
                "id": after.get("id") or before.get("id") or key,
                "identity_key": key,
                "change_class": change_class,
                "before": before_cmp,
                "after": after_cmp,
            }
        )

    policy_changed = base_n.get("policy_hash") != head_n.get("policy_hash")
    classes = [str(a.get("change_class")) for a in added]
    classes.extend(str(r.get("change_class")) for r in removed)
    classes.extend(str(c.get("change_class")) for c in changed)
    addition_n = sum(1 for c in classes if c == "addition")
    expansion_n = sum(1 for c in classes if c == "expansion")
    reduction_n = sum(1 for c in classes if c == "reduction")
    representation_n = sum(1 for c in classes if c == "representation")
    replacement_n = sum(1 for c in classes if c in {"replacement", "mixed"})
    meaningful = bool(
        addition_n
        or expansion_n
        or reduction_n
        or replacement_n
        or policy_changed
        or any(c.get("change_class") == "mixed" for c in changed)
    )
    # Representation-only churn still marks lock drift (hash/path) but is labeled.
    authority_changed = meaningful or bool(changed or added or removed or policy_changed)
    lines = render_lock_diff_lines(added=added, removed=removed, changed=changed)
    return {
        "kind": "authority_lock_delta",
        "summary": {
            "records_added": len(added),
            "records_removed": len(removed),
            "records_changed": len(changed),
            "additions": addition_n,
            "expansions": expansion_n,
            "reductions": reduction_n,
            "replacements": replacement_n,
            "representations": representation_n,
            "policy_changed": policy_changed,
            "authority_changed": authority_changed,
            "meaningful_authority_change": meaningful,
        },
        "changes": {"added": added, "removed": removed, "changed": changed},
        "lines": lines,
    }


def render_lock_diff_lines(
    *,
    added: list[dict[str, Any]],
    removed: list[dict[str, Any]],
    changed: list[dict[str, Any]],
    limit: int = 20,
) -> list[str]:
    lines: list[str] = []
    for rec in added[:limit]:
        pin = rec.get("pin_state") or "unknown"
        caps = ", ".join(rec.get("capabilities") or []) or "authority"
        # Lead with destination host so PR comments keep "who receives it"
        # even when the line is truncated later.
        dest = ", ".join((rec.get("destinations") or [])[:2])
        dest_bit = f" reaches {dest};" if dest else ""
        env = ", ".join((rec.get("env_keys") or [])[:3])
        env_bit = f" passes {env};" if env else ""
        label = rec.get("name") or rec.get("id")
        lines.append(
            f"+ addition {rec.get('kind')} `{label}`:{dest_bit}{env_bit} {caps}; pin={pin}"
        )
    for rec in removed[: max(0, limit - len(lines))]:
        label = rec.get("name") or rec.get("id")
        lines.append(f"- reduction {rec.get('kind')} `{label}`")
    for item in changed[: max(0, limit - len(lines))]:
        after = item.get("after") or {}
        label = after.get("name") or item.get("id")
        klass = item.get("change_class") or "changed"
        lines.append(f"~ {klass} {after.get('kind')} `{label}`")
    return lines


def check_locked(
    root: Path,
    *,
    lock_path: Path | None = None,
    scan: ScanResult | None = None,
) -> tuple[dict[str, Any], int]:
    """Regenerate lock and compare to the committed file. Exit 1 on drift."""
    root = root.resolve()
    path = lock_path or default_lock_path(root)
    if not path.is_file():
        return {
            "ok": False,
            "error": f"Missing {path.name}",
            "hint": "Run `authdiff lock` and commit AUTHORITY.lock.",
            "lines": [],
        }, 1
    on_disk = load_authority_lock(path)
    current = build_authority_lock(root, scan=scan)
    delta = diff_authority_locks(on_disk, current)
    ok = not delta["summary"]["authority_changed"]
    report = {
        "ok": ok,
        "lock": str(path),
        "delta": delta,
        "lines": delta["lines"],
        "verdict": "LOCKED" if ok else "AUTHORITY_CHANGED",
    }
    return report, 0 if ok else 1


def run_lock_command(
    root: Path,
    *,
    check: bool = False,
    update: bool = False,
    lock_path: Path | None = None,
    approval: str | None = None,
    accept_gated: bool = False,
) -> tuple[str, int]:
    root = root.resolve()
    path = lock_path or default_lock_path(root)
    if check and not update:
        report, code = check_locked(root, lock_path=path)
        if report.get("ok"):
            return f"AUTHORITY.lock matches observed authority ({path.name}).", 0
        lines = report.get("lines") or []
        body = "\n".join(lines) if lines else "(authority changed; re-run `authdiff lock`)"
        return (
            f"AUTHORITY.lock out of date — authority changed, needs owner review.\n{body}",
            code,
        )
    try:
        dest, lock = write_authority_lock(
            root,
            path=path,
            approval_owner=approval,
            accept_gated=accept_gated,
        )
    except ValueError as exc:
        return str(exc), 1
    n = len(lock.get("records") or [])
    action = "Updated" if update or path.exists() else "Wrote"
    approval_bit = ""
    if approval and approval.strip():
        approval_bit = f" · approval recorded for {approval.strip()}"
    gated_bit = " · gated findings accepted" if accept_gated else ""
    return f"{action} {dest} ({n} authority records){approval_bit}{gated_bit}.", 0
