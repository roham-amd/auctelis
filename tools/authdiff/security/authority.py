"""Authority Snapshot + AuthorityDelta — the real product unit for authdiff.

A snapshot normalizes each authority-bearing component to capabilities,
destinations, identity hints, approval posture, and pin state. Deltas compare
two snapshots (or a baseline doc) and drive new-only gating / PR comments.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

from authdiff.security.engine import ScanResult
from authdiff.security.fingerprint import component_fingerprint

SNAPSHOT_VERSION = "1.0"
DELTA_VERSION = "1.0"


@dataclass(slots=True)
class AuthorityComponent:
    id: str
    kind: str
    host: str
    path: str
    fingerprint: str
    name: str = ""
    capabilities: list[str] = field(default_factory=list)
    destinations: list[str] = field(default_factory=list)
    identity: list[str] = field(default_factory=list)
    approval_posture: str = "unknown"  # prompt | auto | bypass | unknown
    pin_state: str = "unknown"  # pinned | floating | digest | unknown | n/a
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def logical_authority_id(component: dict[str, Any]) -> str:
    """Stable record id: host/kind/name@file (independent of content digest)."""
    host = str(component.get("host") or component.get("host_id") or component.get("adapter") or "")
    kind = str(component.get("kind") or component.get("type") or "unknown")
    name = str(component.get("name") or component.get("id") or "")
    path = str(component.get("path") or component.get("repository_path") or "").replace("\\", "/")
    return f"{host}/{kind}/{name}@{path}"


def _pin_state(component: dict[str, Any]) -> str:
    hints = set(component.get("priority_hints") or [])
    if "unpinned_package_launcher" in hints:
        return "floating"
    detail = component.get("launcher") or component.get("settings_detail") or {}
    if isinstance(detail, dict):
        pin = str(detail.get("pin_state") or "")
        if pin:
            return pin
    cmd = str(component.get("command") or "").lower()
    args = " ".join(str(a) for a in (component.get("args") or []))
    joined = f"{cmd} {args}"
    if "@sha256:" in joined or "sha256:" in joined:
        return "digest"
    if component.get("type") == "MCP Server Registration":
        # Adapter already classified unpinned; absence means likely pinned or static binary.
        return (
            "pinned"
            if "@" in joined and "unpinned_package_launcher" not in hints
            else ("floating" if any(x in joined for x in ("npx", "uvx", "bunx", "pipx")) else "n/a")
        )
    return "n/a"


def _approval_posture(component: dict[str, Any]) -> str:
    hints = set(component.get("priority_hints") or [])
    detail = component.get("settings_detail") or {}
    if "permission_bypass_flag" in hints or "auto_approve" in hints:
        return "bypass"
    if "auto_running_hook" in hints or "pre_execution_lifecycle" in hints:
        return "auto"
    if isinstance(detail, dict) and detail.get("enableAllProjectMcpServers") is True:
        return "auto"
    if component.get("type") in {"Hook", "Host Settings", "MCP Server Registration"}:
        # MCP tools still require host approval unless a bypass/auto hint fires above.
        return "auto" if "auto_running_hook" in hints else "prompt"
    return "unknown"


def _destinations(component: dict[str, Any]) -> list[str]:
    out: list[str] = []
    url = component.get("url") or component.get("declared_url")
    if url:
        out.append(str(url))
    for key in ("destinations", "external_destinations", "hosts"):
        vals = component.get(key)
        if isinstance(vals, list):
            out.extend(str(v) for v in vals if v)
    return sorted(set(out))


def _identity(component: dict[str, Any]) -> list[str]:
    hints = set(component.get("priority_hints") or [])
    out: list[str] = []
    if "literal_secret_in_env" in hints or "host_secret_inheritance" in hints:
        env = component.get("env") or {}
        if isinstance(env, dict):
            out.extend(sorted(str(k) for k in env))
        else:
            out.append("env_credentials")
    if "base_url_or_proxy_override" in hints:
        out.append("anthropic_base_url_override")
    return out


def _capabilities(component: dict[str, Any], findings: list[Any]) -> list[str]:
    caps: set[str] = set()
    cid = str(component.get("component_id") or "")
    for finding in findings:
        ids = (
            finding.component_ids
            if hasattr(finding, "component_ids")
            else (finding.get("component_ids") or [])
        )
        if cid and cid not in ids:
            continue
        for cap in (
            finding.capabilities
            if hasattr(finding, "capabilities")
            else (finding.get("capabilities") or [])
        ):
            caps.add(str(cap))
    hints = set(component.get("priority_hints") or [])
    if "possible_execution_boundary" in hints or "download_and_execute" in hints:
        caps.add("execute")
    if "literal_secret_in_env" in hints or "host_secret_inheritance" in hints:
        caps.add("access_secrets")
    if component.get("url") or "external_url_reference" in hints:
        caps.add("access_network")
    return sorted(caps)


def build_authority_snapshot(scan: ScanResult) -> dict[str, Any]:
    """Build a canonical Authority Snapshot from a scan result."""
    components_out: list[dict[str, Any]] = []
    for raw in scan.inventory.get("components") or []:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type") or "unknown")
        # Skip pure inventory hosts with no authority signal unless they carry hints.
        hints = list(raw.get("priority_hints") or [])
        authority_kinds = {
            "MCP Server Registration",
            "Hook",
            "Host Settings",
            "Skill",
            "Rule / instruction file",
            "Rule pack",
            "CI Workflow",
            "Plugin",
        }
        if kind not in authority_kinds and not hints:
            continue
        fp = str(raw.get("fingerprint") or component_fingerprint(raw))
        cid = str(raw.get("component_id") or fp)
        name = str(raw.get("name") or "")
        comp = AuthorityComponent(
            id=cid,
            kind=kind,
            host=str(raw.get("host_id") or raw.get("adapter") or ""),
            path=str(raw.get("repository_path") or raw.get("name") or ""),
            fingerprint=fp,
            name=name,
            capabilities=_capabilities(raw, scan.findings),
            destinations=_destinations(raw),
            identity=_identity(raw),
            approval_posture=_approval_posture(raw),
            pin_state=_pin_state(raw),
            evidence=[str(raw.get("repository_path") or "")],
        )
        components_out.append(comp.to_dict())

    components_out.sort(key=lambda c: (c["kind"], c["path"], c.get("name") or "", c["fingerprint"]))
    body = {
        "snapshot_version": SNAPSHOT_VERSION,
        "product": "authdiff",
        "product_version": scan.product_version,
        "repository": scan.repository_path,
        "audited_commit": scan.commit,
        "collected_at_utc": scan.collected_at_utc,
        "components": components_out,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["snapshot_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return body


def diff_authority_snapshots(
    base: dict[str, Any],
    head: dict[str, Any],
) -> dict[str, Any]:
    """Compute AuthorityDelta between two snapshots."""
    base_by_fp = {
        str(c.get("fingerprint")): c for c in (base.get("components") or []) if isinstance(c, dict)
    }
    head_by_fp = {
        str(c.get("fingerprint")): c for c in (head.get("components") or []) if isinstance(c, dict)
    }
    # Logical identity (host/kind/name@path) — not bare path — so multi-server
    # files do not collapse to a single last-write-wins entry.
    base_by_logical = {
        logical_authority_id(c): c for c in (base.get("components") or []) if isinstance(c, dict)
    }
    head_by_logical = {
        logical_authority_id(c): c for c in (head.get("components") or []) if isinstance(c, dict)
    }

    added = [head_by_fp[fp] for fp in sorted(set(head_by_fp) - set(base_by_fp))]
    removed = [base_by_fp[fp] for fp in sorted(set(base_by_fp) - set(head_by_fp))]

    escalated: list[dict[str, Any]] = []
    approval_weakened: list[dict[str, Any]] = []
    pin_loosened: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []

    for key in sorted(set(base_by_logical) & set(head_by_logical)):
        before, after = base_by_logical[key], head_by_logical[key]
        if before.get("fingerprint") == after.get("fingerprint"):
            continue
        path = str(after.get("path") or before.get("path") or key)
        modified.append({"path": path, "logical_id": key, "before": before, "after": after})
        before_caps = set(before.get("capabilities") or [])
        after_caps = set(after.get("capabilities") or [])
        if after_caps - before_caps:
            escalated.append(
                {
                    "path": path,
                    "added_capabilities": sorted(after_caps - before_caps),
                    "before": before,
                    "after": after,
                }
            )
        posture_rank = {"prompt": 0, "unknown": 1, "auto": 2, "bypass": 3}
        if posture_rank.get(str(after.get("approval_posture")), 1) > posture_rank.get(
            str(before.get("approval_posture")), 1
        ):
            approval_weakened.append({"path": path, "before": before, "after": after})
        pin_rank = {"digest": 0, "pinned": 1, "n/a": 2, "unknown": 3, "floating": 4}
        if pin_rank.get(str(after.get("pin_state")), 3) > pin_rank.get(
            str(before.get("pin_state")), 3
        ):
            pin_loosened.append({"path": path, "before": before, "after": after})

    return {
        "delta_version": DELTA_VERSION,
        "kind": "authority_delta",
        "base_hash": base.get("snapshot_hash"),
        "head_hash": head.get("snapshot_hash"),
        "summary": {
            "components_added": len(added),
            "components_removed": len(removed),
            "components_modified": len(modified),
            "capabilities_escalated": len(escalated),
            "approval_weakened": len(approval_weakened),
            "pin_loosened": len(pin_loosened),
            "high_authority_added": len(added)
            + len(escalated)
            + len(approval_weakened)
            + len(pin_loosened),
        },
        "changes": {
            "added": added,
            "removed": removed,
            "modified": modified,
            "escalated": escalated,
            "approval_weakened": approval_weakened,
            "pin_loosened": pin_loosened,
        },
    }


def render_component_delta_lines(delta: dict[str, Any], *, limit: int = 5) -> list[str]:
    """Human lines for PR comment / terminal: + MCP foo: exec via npx (unpinned)…"""
    lines: list[str] = []
    changes = delta.get("changes") or {}
    for comp in (changes.get("added") or [])[:limit]:
        caps = ", ".join(comp.get("capabilities") or []) or "authority"
        pin = comp.get("pin_state") or "unknown"
        posture = comp.get("approval_posture") or "unknown"
        dest = ", ".join((comp.get("destinations") or [])[:2])
        dest_bit = f", reaches {dest}" if dest else ""
        ident = ", ".join((comp.get("identity") or [])[:3])
        ident_bit = f", passes {ident}" if ident else ""
        label = comp.get("name") or comp.get("path")
        lines.append(
            f"+ {comp.get('kind')} `{label}`: {caps}; "
            f"pin={pin}; approvals={posture}{ident_bit}{dest_bit}"
        )
    for item in (changes.get("escalated") or [])[: max(0, limit - len(lines))]:
        added = ", ".join(item.get("added_capabilities") or [])
        lines.append(f"~ `{item.get('path')}` escalated capabilities: +{added}")
    for item in (changes.get("approval_weakened") or [])[: max(0, limit - len(lines))]:
        before = (item.get("before") or {}).get("approval_posture")
        after = (item.get("after") or {}).get("approval_posture")
        lines.append(f"~ `{item.get('path')}` approvals: {before} → {after}")
    for item in (changes.get("pin_loosened") or [])[: max(0, limit - len(lines))]:
        before = (item.get("before") or {}).get("pin_state")
        after = (item.get("after") or {}).get("pin_state")
        lines.append(f"~ `{item.get('path')}` pin: {before} → {after}")
    return lines
