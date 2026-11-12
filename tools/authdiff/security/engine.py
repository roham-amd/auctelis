"""Orchestrate inventory → capabilities → rules → scan artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from authdiff.inventory.collector import collect_inventory, inventory_to_json
from authdiff.preflight import inventory_to_graph, resolve_git_commit
from authdiff.security.capabilities import authority_bearing_component_ids, extract_capabilities
from authdiff.security.evidence_util import EvidenceContext, enrich_component_provenance
from authdiff.security.fingerprint import component_fingerprint
from authdiff.security.models import Capability, Evidence, Finding, Relationship
from authdiff.security.relationships import emit_relationships
from authdiff.security.rules import CROSS_COMPONENT_RULE_IDS, RULES, apply_all_rules
from authdiff.versioning import package_version, product_version


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

    @classmethod
    def from_findings_doc(cls, doc: dict[str, Any]) -> ScanResult:
        """Rebuild a ScanResult from ``findings.json`` (explain / risk-diff helpers)."""
        findings = [
            Finding(
                finding_id=str(f.get("finding_id") or ""),
                rule_id=str(f.get("rule_id") or ""),
                title=str(f.get("title") or ""),
                severity=f.get("severity") or "INFORMATIONAL",  # type: ignore[arg-type]
                confidence=f.get("confidence") or "POTENTIAL",  # type: ignore[arg-type]
                description=str(f.get("description") or ""),
                component_ids=list(f.get("component_ids") or []),
                evidence_ids=list(f.get("evidence_ids") or []),
                capabilities=list(f.get("capabilities") or []),
                attacker_control=str(f.get("attacker_control") or ""),
                entry_point=str(f.get("entry_point") or ""),
                trust_boundary=str(f.get("trust_boundary") or ""),
                impact=str(f.get("impact") or ""),
                missing_controls=list(f.get("missing_controls") or []),
                recommended_action=str(f.get("recommended_action") or ""),
                exploitability=str(f.get("exploitability") or "UNKNOWN"),
                exposure=str(f.get("exposure") or "UNKNOWN"),
                finding_class=f.get("finding_class") or "SECURITY_FINDING",  # type: ignore[arg-type]
                evidence_strength=f.get("evidence_strength") or "INFERRED_HINT",  # type: ignore[arg-type]
                verify_in_60s=str(f.get("verify_in_60s") or ""),
                fix_snippet=str(f.get("fix_snippet") or ""),
            )
            for f in doc.get("findings") or []
        ]
        evidences = [
            Evidence(
                evidence_id=str(e.get("evidence_id") or ""),
                component_id=e.get("component_id"),
                evidence_class=e.get("evidence_class") or "SOURCE_STATIC",  # type: ignore[arg-type]
                verification_status=e.get("verification_status") or "OBSERVED",  # type: ignore[arg-type]
                file_path=e.get("file_path"),
                line_start=e.get("line_start"),
                line_end=e.get("line_end"),
                content_digest=e.get("content_digest"),
                collection_method=str(e.get("collection_method") or "deterministic_rule"),
                source_commit=e.get("source_commit"),
                observed_at=e.get("observed_at"),
                limitations=list(e.get("limitations") or []),
                summary=str(e.get("summary") or ""),
                authority_layer=e.get("authority_layer") or "CONFIGURED",  # type: ignore[arg-type]
                parser_version=e.get("parser_version"),
                rule_pack_version=e.get("rule_pack_version"),
                derived_from=list(e.get("derived_from") or []),
            )
            for e in doc.get("evidence_registry") or []
        ]
        summary = doc.get("summary") or {}
        return cls(
            repository_path=str(doc.get("repository") or ""),
            commit=doc.get("audited_commit"),
            collected_at_utc=str(doc.get("collected_at_utc") or ""),
            inventory={"components": []},
            graph={},
            capabilities=[],
            evidences=evidences,
            findings=findings,
            coverage=doc.get("coverage") or {},
            authority_bearing_count=int(summary.get("authority_bearing_components") or 0),
            external_destination_count=int(summary.get("external_data_destinations") or 0),
            product_version=str(doc.get("product_version") or ""),
            package_version=str(doc.get("package_version") or ""),
            rules_applied=list(doc.get("rules_applied") or []),
        )

    def to_findings_doc(self) -> dict[str, Any]:
        from authdiff.inventory.coverage import AUTHORITY_LAYERS
        from authdiff.versioning import load_versions

        by_class = self.findings_by_class()
        versions = load_versions()
        return {
            "findings_version": "1.2",
            "product": "authdiff",
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

    def finding_by_id(self, finding_id: str) -> Finding | None:
        for finding in self.findings:
            if finding.finding_id == finding_id:
                return finding
        return None


def run_security_scan(target: Path, *, default_excludes: bool = True) -> ScanResult:
    target = target.resolve()
    result = collect_inventory(target, default_excludes=default_excludes)
    commit = resolve_git_commit(target)
    collected_at = result.collected_at_utc
    inventory = inventory_to_json(result)
    if commit:
        inventory["repository_commit"] = commit

    components = list(result.components)
    enrich_component_provenance(components, root=target)
    for component in components:
        component["fingerprint"] = component_fingerprint(component)
    # Mirror fingerprints into serialized inventory.
    for inv_comp in inventory.get("components") or []:
        cid = inv_comp.get("component_id")
        match = next((c for c in components if c.get("component_id") == cid), None)
        if match:
            inv_comp["content_digest"] = match.get("content_digest")
            inv_comp["fingerprint"] = match.get("fingerprint")

    capabilities = extract_capabilities(components)
    ctx = EvidenceContext(
        repository_root=target,
        source_commit=commit,
        observed_at=collected_at,
    )
    evidences, findings = apply_all_rules(components, ctx=ctx)

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
    relationships = emit_relationships(components)

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
        rules_applied=[r.rule_id for r in RULES] + list(CROSS_COMPONENT_RULE_IDS),
        relationships=relationships,
    )
