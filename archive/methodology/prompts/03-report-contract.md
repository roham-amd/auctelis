# AESA Report Contract (v1.0)

Operator reference for machine-readable output. Narrative report: Section 21 in `01-core-prompt.md`.

**Schema files (repo root):**

- `schemas/audit-report.schema.json`
- `schemas/AI_Agent_Ecosystem_Security_Audit_v1.schema.json` (same contract)

**Examples:**

- `examples/sample-audit-context.yaml`
- `examples/sample-component-inventory.json`
- `examples/sample-audit-summary.json`

---

# 22. MACHINE-READABLE JSON CONTRACT

## 22.1 Top-level JSON template

```json
{
  "audit_version": "1.0",
  "repository": "",
  "repository_role": "Unknown",
  "repository_visibility": "Unknown",
  "audited_commit": null,
  "tree_sha": null,
  "previous_audited_commit": null,
  "audit_mode": "full",
  "workflow_mode": "discovery_then_risk_prioritized_deep_audit",
  "audit_scope_mode": "catalog_inventory",
  "audit_date_utc": "",
  "environment_mode": "DEGRADED_READ_ONLY",
  "repository_decision": "ECOSYSTEM_INVENTORY_ONLY",
  "overall_risk_rating": "INSUFFICIENT EVIDENCE",
  "evidence_confidence": "NONE",
  "capability_matrix": [],
  "component_inventory": {
    "total_discovered": 0,
    "deeply_reviewed": 0,
    "partially_reviewed": 0,
    "inventory_only": 0,
    "not_reviewed": 0,
    "out_of_scope": 0,
    "external_references": 0,
    "external_sources_deeply_reviewed": 0,
    "pending_batches": []
  },
  "risk_dimensions": {
    "component_security_risk": "INSUFFICIENT EVIDENCE",
    "agent_authority_runtime_risk": "INSUFFICIENT EVIDENCE",
    "supply_chain_trust_risk": "INSUFFICIENT EVIDENCE",
    "production_data_protection_risk": "INSUFFICIENT EVIDENCE"
  },
  "components": [],
  "external_sources": [],
  "cross_component_analysis": {
    "performed": false,
    "interaction_graph_reference": null,
    "tool_chaining_reviewed": false,
    "delegation_reviewed": false,
    "hook_interactions_reviewed": false,
    "automation_interactions_reviewed": false,
    "workflow_interactions_reviewed": false,
    "shared_credentials_reviewed": false,
    "shared_memory_reviewed": false,
    "tool_shadowing_reviewed": false,
    "approval_bypass_reviewed": false,
    "tenant_isolation_reviewed": false,
    "cross_component_risks": []
  },
  "coverage": {
    "population_defined": false,
    "applicable_surfaces": null,
    "reviewed": null,
    "not_verified": null,
    "not_reviewed": null,
    "not_applicable": null,
    "omissions": []
  },
  "trust_chain": {
    "source_identity_verified": null,
    "artifact_identity_verified": null,
    "artifact_digest_verified": null,
    "signature_verified": null,
    "provenance_verified": null,
    "source_artifact_traceability_verified": null,
    "host_permissions_verified": null,
    "runtime_configuration_verified": null,
    "runtime_behavior_tested": false
  },
  "observations": {
    "prompt_injection_found": null,
    "tool_poisoning_found": null,
    "tool_shadowing_or_collision_found": null,
    "dynamic_metadata_drift_found": null,
    "excessive_agency_found": null,
    "unauthorized_tool_access_confirmed": null,
    "sensitive_data_exfiltration_confirmed": null,
    "cross_tenant_issue_confirmed": null,
    "malicious_behavior_confirmed": null,
    "malicious_package_match": null,
    "active_or_historical_secret_exposure_confirmed": null,
    "external_data_transmission_confirmed": null,
    "oauth_confused_deputy_found": null,
    "approval_replay_or_bypass_found": null,
    "memory_or_context_poisoning_found": null,
    "hook_execution_risk_found": null,
    "unsafe_automation_found": null,
    "subagent_privilege_escalation_found": null,
    "cross_component_attack_path_found": null,
    "model_supply_chain_issue_found": null,
    "browser_agent_security_issue_found": null,
    "cloud_infrastructure_issue_found": null
  },
  "findings_count": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "informational": 0
  },
  "findings": [],
  "evidence_registry": [],
  "modules_applied": [],
  "sbom": {
    "generated": false,
    "format": null,
    "tool": null,
    "tool_version": null,
    "scope": null,
    "digest": null,
    "limitations": []
  },
  "component_hard_gates": [],
  "cross_component_hard_gates": [],
  "conditions": [],
  "unverified_critical_areas": [],
  "limitations": [],
  "follow_on_test_plan_required": null,
  "json_validation_status": "NOT VALIDATED",
  "score_type": "NONE",
  "score": null,
  "recommend_production_use": false
}
```

## 22.2 Component JSON record

```json
{
  "component_id": "C-001",
  "name": "",
  "type": "Unknown",
  "reference_kind": "UNKNOWN",
  "repository_path": null,
  "source_type": "Unknown",
  "source_reference": null,
  "source_commit": null,
  "version": null,
  "artifact_reference": null,
  "artifact_digest": null,
  "publisher": null,
  "installation_method": "Unknown",
  "update_policy": "Unknown",
  "host_agent": "Unknown",
  "host_version": null,
  "capabilities": [],
  "sensitive_permissions": [],
  "external_destinations": [],
  "execution_model": null,
  "discovery_status": "IDENTIFIED",
  "source_review_status": "NOT VERIFIED",
  "artifact_integrity_status": "NOT VERIFIED",
  "source_artifact_traceability_status": "NOT VERIFIED",
  "host_integration_status": "NOT VERIFIED",
  "runtime_review_status": "NOT VERIFIED",
  "cross_component_review_status": "NOT VERIFIED",
  "coverage": {
    "applicable_surfaces": null,
    "reviewed": null,
    "not_verified": null,
    "not_reviewed": null,
    "not_applicable": null
  },
  "risk_dimensions": {
    "component_security_risk": "INSUFFICIENT EVIDENCE",
    "agent_authority_runtime_risk": "INSUFFICIENT EVIDENCE",
    "supply_chain_trust_risk": "INSUFFICIENT EVIDENCE",
    "production_data_protection_risk": "INSUFFICIENT EVIDENCE"
  },
  "evidence_confidence": "NONE",
  "risk_rating": "INSUFFICIENT EVIDENCE",
  "component_security_decision": "INSUFFICIENT EVIDENCE",
  "production_suitability_decision": "INSUFFICIENT EVIDENCE",
  "allowed_restricted_use": null,
  "prohibited_use": [],
  "finding_ids": [],
  "hard_gates": [],
  "conditions": [],
  "evidence_ids": [],
  "unverified_areas": [],
  "limitations": []
}
```

## 22.3 Gate JSON record

```json
{
  "gate_id": "C-G09",
  "status": "NOT VERIFIED",
  "requirement": "Effective permissions must be bounded",
  "evidence_ids": [],
  "blocker": true,
  "remediation": "Provide independently verified host and backend authorization evidence"
}
```

## 22.5 Formal JSON Schema

A companion JSON Schema file is provided as `AI_Agent_Ecosystem_Security_Audit_v1.schema.json` using JSON Schema Draft 2020-12. Use it to validate the machine-readable summary. The schema is a structural contract, not proof that the underlying findings are true. Update the schema URI to an organization-controlled location before publishing internally. Do not claim successful validation unless a real validator was executed and its version/result recorded.

## 22.4 JSON consistency rules

- `null` means unknown/not assessed; do not use false to represent unknown.
- Boolean `false` is allowed only when false has been verified.
- Counts must come from the defined inventory and actual work records.
- Coverage counts must be internally consistent and use an explicit denominator.
- `recommend_production_use` must remain `false` unless all applicable production gates pass for exact selected components, artifacts, host configuration, and deployment context.
- Restricted-use approval must remain explicitly restricted and must not be treated as general production approval.
- `runtime_behavior_tested` is `false` in this passive audit unless separately authorized runtime evidence is actually included and identified.
- If JSON is not validated by a real validator, retain `NOT VALIDATED`.

---

# 23. OUTPUT FILES AND STATE MANAGEMENT

If persistent file creation is genuinely available, keep outputs outside the target repository:

```text
security-audit-report.md
security-audit-summary.json
audit-state.json
repository-inventory.json
component-inventory.json
component-assessments/
findings.json
evidence-registry.json
external-source-registry.json
tool-capability-matrix.json
component-interaction-graph.json
data-flow-map.json
coverage-ledger.json
security-audit-summary.schema.json
```

Compute SHA-256/SHA-512 only with an actual hashing tool. Record tool/version and input. Never invent paths, hashes, scan results, or persistent state. If persistent files cannot be created, provide the report/JSON in the response and explicitly state no persistent files/state were created.

---

