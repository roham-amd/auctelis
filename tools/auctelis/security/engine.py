"""Orchestrate inventory → capabilities → rules → scan artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auctelis.inventory.collector import collect_inventory, inventory_to_json
from auctelis.inventory.limits import CollectorLimits
from auctelis.preflight import inventory_to_graph, resolve_git_commit
from auctelis.security.capabilities import authority_bearing_component_ids, extract_capabilities
from auctelis.security.evidence_util import EvidenceContext, enrich_component_provenance
from auctelis.security.fingerprint import component_fingerprint
from auctelis.security.models import Capability, Evidence, Finding, Relationship
from auctelis.security.relationships import emit_relationships
from auctelis.versioning import package_version, product_version

# Research rules live in ``auctelis_research`` (omitted from the product wheel).
# ``apply_rules=True`` lazy-loads them for auctelis-dev from a source checkout.


@dataclass(slots=True)
class ScanResult:
    repository_path: str
    commit: str | None
    collected_at_utc: str
    inventory: dict[str, Any]
    graph: dict[str, Any]
    capabilities: list[Capability]
    evidences: list[Evidence]
    findings: list[Finding]
    coverage: dict[str, Any]
    authority_bearing_count: int
    external_destination_count: int
    product_version: str
    package_version: str
    rules_applied: list[str]
    relationships: list[Relationship] | None = None

    def findings_by_severity(self) -> dict[str, int]:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFORMATIONAL": 0}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        return counts

    def findings_by_class(self) -> dict[str, int]:
        counts = {"CAPABILITY": 0, "EXPOSURE": 0, "SECURITY_FINDING": 0}
        for finding in self.findings:
            counts[finding.finding_class] = counts.get(finding.finding_class, 0) + 1
        return counts

    def to_findings_doc(self) -> dict[str, Any]:
        from auctelis.inventory.coverage import AUTHORITY_LAYERS
        from auctelis.versioning import load_versions

        by_class = self.findings_by_class()
        versions = load_versions()
        return {
            "findings_version": "1.2",
            "product": "auctelis",
            "product_version": self.product_version,
            "package_version": self.package_version,
            "repository": self.repository_path,
            "audited_commit": self.commit,
            "collected_at_utc": self.collected_at_utc,
            "rules_applied": self.rules_applied,
            "provenance": {
                "product_version": self.product_version,
                "package_version": self.package_version,
                "rule_pack": versions.get("rule_pack"),
                "findings_contract": versions.get("findings_contract"),
                "authority_lock": versions.get("authority_lock"),
                "audited_commit": self.commit,
                "collected_at_utc": self.collected_at_utc,
            },
            "authority_layers": AUTHORITY_LAYERS,
            "summary": {
                "component_count": len(self.inventory.get("components") or []),
                "authority_bearing_components": self.authority_bearing_count,
                "external_data_destinations": self.external_destination_count,
                "finding_count": len(self.findings),
                "by_severity": self.findings_by_severity(),
                "by_finding_class": by_class,
                "security_findings": by_class.get("SECURITY_FINDING", 0),
                "exposure_observations": by_class.get("EXPOSURE", 0),
                "capability_observations": by_class.get("CAPABILITY", 0),
            },
            "capabilities": [c.to_dict() for c in self.capabilities],
            "evidence_registry": [e.to_dict() for e in self.evidences],
            "findings": [f.to_dict() for f in self.findings],
            "relationships": [r.to_dict() for r in (self.relationships or [])],
            "coverage": self.coverage,
            "limitations": [
                "Deterministic rules produce OBSERVED/POTENTIAL findings, not confirmed exploits.",
                "CAPABILITY observations are not vulnerabilities; SECURITY_FINDING requires "
                "exposure conditions and missing controls.",
                "Passive scans establish DECLARED/CONFIGURED authority only.",
                "Host EFFECTIVE permissions and VERIFIED runtime behavior remain NOT VERIFIED.",
                "Incomplete adapter coverage means absence of findings is not evidence of safety.",
            ],
        }


def run_security_scan(
    target: Path,
    *,
    default_excludes: bool = True,
    apply_rules: bool = True,
    limits: CollectorLimits | None = None,
) -> ScanResult:
    """Inventory a tree and optionally apply the research rule pack.

    Product path (``check`` / ``lock`` / ``gate``) uses ``apply_rules=False`` —
    the gate is lock-only. ``auctelis-dev scan`` keeps ``apply_rules=True``.
    """
    target = target.resolve()
    result = collect_inventory(target, default_excludes=default_excludes, limits=limits)
    commit = resolve_git_commit(target)
    collected_at = result.collected_at_utc
    inventory = inventory_to_json(result)
    if commit:
        inventory["repository_commit"] = commit

    components = list(result.components)
    enrich_component_provenance(components, root=target)
    for component in components:
        component["fingerprint"] = component_fingerprint(component)
    # Mirror fingerprints into serialized inventory (index once; avoid O(n²)).
    components_by_id = {c.get("component_id"): c for c in components}
    for inv_comp in inventory.get("components") or []:
        match = components_by_id.get(inv_comp.get("component_id"))
        if match:
            inv_comp["content_digest"] = match.get("content_digest")
            inv_comp["fingerprint"] = match.get("fingerprint")

    capabilities = extract_capabilities(components)
    ctx = EvidenceContext(
        repository_root=target,
        source_commit=commit,
        observed_at=collected_at,
    )
    if apply_rules:
        try:
            from auctelis_research.rules import CROSS_COMPONENT_RULE_IDS, RULES, apply_all_rules
        except ImportError as exc:
            raise RuntimeError(
                "Research rules are not in the product wheel; "
                "run auctelis-dev from a source checkout."
            ) from exc
        evidences, findings = apply_all_rules(components, ctx=ctx)
        rules_applied = [r.rule_id for r in RULES] + list(CROSS_COMPONENT_RULE_IDS)
    else:
        evidences, findings = [], []
        rules_applied = []

    # Attach inventory evidence stubs for capability references.
    for comp in components:
        cid = str(comp.get("component_id") or "")
        evidences.append(
            Evidence(
                evidence_id=f"E-INV-{cid}",
                component_id=cid,
                evidence_class="SOURCE_STATIC",
                verification_status="OBSERVED",
                file_path=comp.get("repository_path"),
                content_digest=comp.get("content_digest"),
                collection_method="inventory_adapter",
                source_commit=commit,
                observed_at=collected_at,
                summary=f"Component discovered by adapter `{comp.get('adapter')}`.",
                limitations=["Discovery only; does not prove runtime loading."],
            )
        )

    authority_ids = authority_bearing_component_ids(capabilities)
    external = sum(
        1
        for c in capabilities
        if c.kind == "access_network" and c.status in {"OBSERVED", "POTENTIAL", "CONFIRMED"}
    )
    # Cross-component relationship graphs are research output. The product
    # check/lock/gate paths never read them, and emitting them here is
    # quadratic on large repositories.
    relationships = emit_relationships(components) if apply_rules else []

    return ScanResult(
        repository_path=str(target),
        commit=commit,
        collected_at_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        inventory=inventory,
        graph=inventory_to_graph(result, commit=commit, audit_id="scan-guard"),
        capabilities=capabilities,
        evidences=evidences,
        findings=findings,
        coverage=result.coverage or {},
        authority_bearing_count=len(authority_ids),
        external_destination_count=external,
        product_version=product_version(),
        package_version=package_version(),
        rules_applied=rules_applied,
        relationships=relationships,
    )


def run_authority_inventory(
    target: Path,
    *,
    default_excludes: bool = True,
    limits: CollectorLimits | None = None,
) -> ScanResult:
    """Product inventory: adapters + capabilities, no rule findings."""
    return run_security_scan(
        target,
        default_excludes=default_excludes,
        apply_rules=False,
        limits=limits,
    )
