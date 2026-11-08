from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$|^[A-Za-z0-9+/=]+$")  # sha256 hex or base64-ish


@dataclass
class SemanticIssue:
    code: str
    message: str
    path: str = ""


@dataclass
class SemanticResult:
    ok: bool
    issues: list[SemanticIssue] = field(default_factory=list)


def issue(code: str, message: str, path: str = "") -> SemanticIssue:
    return SemanticIssue(code=code, message=message, path=path)


def validate_semantics(report: dict[str, Any]) -> SemanticResult:
    issues: list[SemanticIssue] = []

    components = report.get("components") or []
    findings = report.get("findings") or []
    evidence = report.get("evidence_registry") or []

    component_ids = {c.get("component_id") for c in components if c.get("component_id")}
    evidence_ids = {e.get("evidence_id") for e in evidence if e.get("evidence_id")}
    finding_ids = {f.get("finding_id") for f in findings if f.get("finding_id")}

    if len(component_ids) != len(components):
        issues.append(issue("DUPLICATE_ID", "component_id values must be unique", "components"))
    if len(evidence_ids) != len(evidence):
        issues.append(
            issue("DUPLICATE_ID", "evidence_id values must be unique", "evidence_registry")
        )
    if len(finding_ids) != len(findings):
        issues.append(issue("DUPLICATE_ID", "finding_id values must be unique", "findings"))

    for idx, ev in enumerate(evidence):
        eid = ev.get("evidence_id")
        cid = ev.get("component_id")
        if cid and cid not in component_ids:
            issues.append(
                issue(
                    "DANGLING_COMPONENT_REF",
                    f"evidence {eid} references unknown component_id {cid}",
                    f"evidence_registry[{idx}]",
                )
            )
        ts = ev.get("retrieval_date_utc")
        if ts and not RFC3339_RE.match(str(ts)):
            issues.append(
                issue(
                    "INVALID_TIMESTAMP",
                    f"retrieval_date_utc must be RFC 3339 UTC: {ts}",
                    f"evidence_registry[{idx}]",
                )
            )
        digest = ev.get("artifact_digest")
        if digest and not DIGEST_RE.match(str(digest)):
            issues.append(
                issue(
                    "INVALID_DIGEST",
                    f"artifact_digest format not recognized: {digest}",
                    f"evidence_registry[{idx}]",
                )
            )

    for idx, comp in enumerate(components):
        for eid in comp.get("evidence_ids") or []:
            if eid not in evidence_ids:
                issues.append(
                    issue(
                        "DANGLING_EVIDENCE_REF",
                        f"component {comp.get('component_id')} references missing evidence {eid}",
                        f"components[{idx}].evidence_ids",
                    )
                )
        for fid in comp.get("finding_ids") or []:
            if fid not in finding_ids:
                issues.append(
                    issue(
                        "DANGLING_FINDING_REF",
                        f"component {comp.get('component_id')} references missing finding {fid}",
                        f"components[{idx}].finding_ids",
                    )
                )

    severity_buckets = {"critical", "high", "medium", "low", "informational"}
    counts = report.get("findings_count") or {}
    for bucket in severity_buckets:
        if bucket not in counts:
            issues.append(
                issue("MISSING_COUNT", f"findings_count.{bucket} required", "findings_count")
            )

    if counts:
        for sev, key in [
            ("CRITICAL", "critical"),
            ("HIGH", "high"),
            ("MEDIUM", "medium"),
            ("LOW", "low"),
            ("INFORMATIONAL", "informational"),
        ]:
            actual = sum(1 for f in findings if f.get("severity") == sev)
            declared = counts.get(key, 0)
            if actual != declared:
                issues.append(
                    issue(
                        "FINDINGS_COUNT_MISMATCH",
                        f"findings_count.{key}={declared} but {actual} findings have severity {sev}",
                        "findings_count",
                    )
                )

    for idx, finding in enumerate(findings):
        fid = finding.get("finding_id")
        for cid in finding.get("affected_component_ids") or []:
            if cid not in component_ids:
                issues.append(
                    issue(
                        "DANGLING_COMPONENT_REF",
                        f"finding {fid} references unknown component_id {cid}",
                        f"findings[{idx}].affected_component_ids",
                    )
                )
        label = finding.get("evidence_label")
        eids = finding.get("evidence_ids") or []
        for eid in eids:
            if eid not in evidence_ids:
                issues.append(
                    issue(
                        "DANGLING_EVIDENCE_REF",
                        f"finding {fid} references missing evidence {eid}",
                        f"findings[{idx}].evidence_ids",
                    )
                )
        if label == "CONFIRMED" and not eids:
            issues.append(
                issue(
                    "UNSUPPORTED_CLAIM",
                    f"finding {fid} is CONFIRMED but cites no evidence_ids",
                    f"findings[{idx}]",
                )
            )

    trust = report.get("trust_chain") or {}
    runtime_tested = trust.get("runtime_behavior_tested")
    has_runtime_evidence = any((e.get("evidence_type") == "RUNTIME") for e in evidence)
    if runtime_tested and not has_runtime_evidence:
        issues.append(
            issue(
                "RUNTIME_MISLABEL",
                "trust_chain.runtime_behavior_tested=true but no RUNTIME evidence records exist",
                "trust_chain",
            )
        )

    inv = report.get("component_inventory") or {}
    total = inv.get("total_discovered")
    if total is not None and total < len(components):
        issues.append(
            issue(
                "INVENTORY_COUNT",
                "component_inventory.total_discovered is less than components[] length",
                "component_inventory.total_discovered",
            )
        )

    for gate_list_name in ("component_hard_gates", "cross_component_hard_gates"):
        for gidx, gate in enumerate(report.get(gate_list_name) or []):
            for eid in gate.get("evidence_ids") or []:
                if eid not in evidence_ids:
                    issues.append(
                        issue(
                            "DANGLING_EVIDENCE_REF",
                            f"gate {gate.get('gate_id')} references missing evidence {eid}",
                            f"{gate_list_name}[{gidx}]",
                        )
                    )

    for comp in components:
        for gate in comp.get("hard_gates") or []:
            for eid in gate.get("evidence_ids") or []:
                if eid not in evidence_ids:
                    issues.append(
                        issue(
                            "DANGLING_EVIDENCE_REF",
                            f"component gate references missing evidence {eid}",
                            f"components[{comp.get('component_id')}].hard_gates",
                        )
                    )

    return SemanticResult(ok=len(issues) == 0, issues=issues)
