# authdiff / authdiff JSON schemas

Machine-readable contracts for authdiff artifacts and (legacy) audit engagements.

Canonical **audit report** source of truth:

- Edit: [`../canonical/schemas/audit-report.schema.json`](../canonical/schemas/audit-report.schema.json)
- Publish aliases: `authdiff-dev build schemas` → this directory

Validate instances:

```bash
authdiff-dev validate report path/to/summary.json
authdiff-dev validate graph path/to/ecosystem-graph.json
authdiff-dev validate claim path/to/claim.json
```

---

## Product-critical schema

| File | Version | Purpose |
| --- | --- | --- |
| [`authority-lock.schema.json`](authority-lock.schema.json) | lock `version` **1** | **`AUTHORITY.lock`** — approved authority baseline (north-star artifact) |
| [`authority-policy.schema.json`](authority-policy.schema.json) | policy contract | `.authdiff.yml` / gate policy shape |
| [`agent-authority-manifest.schema.json`](agent-authority-manifest.schema.json) | `authdiff.authority_manifest.v1` | Declared vs observed Agent Authority Manifest |

Semantic contract for the lock (identity, expansion/reduction/representation):
[`../docs/AUTHORITY-LOCK.md`](../docs/AUTHORITY-LOCK.md).

---

## Schema catalog

| File | Version field | Purpose |
| --- | --- | --- |
| [`audit-report.schema.json`](audit-report.schema.json) | `audit_version` **1.0** | Narrative engagement summary JSON |
| [`AI_Agent_Ecosystem_Security_Audit_v1.schema.json`](AI_Agent_Ecosystem_Security_Audit_v1.schema.json) | same | Legacy filename alias |
| [`ecosystem-graph.schema.json`](ecosystem-graph.schema.json) | `graph_version` **1.0** | Nodes/edges/attack_paths seed |
| [`audit-manifest.schema.json`](audit-manifest.schema.json) | `manifest_version` **1.0** | Engagement scope / acquisition metadata |
| [`audit-diff.schema.json`](audit-diff.schema.json) | `diff_version` **1.0** | Structural report/graph diffs |
| [`evidence-digest-manifest.schema.json`](evidence-digest-manifest.schema.json) | `manifest_version` **1.0** | Evidence digest inventory |
| [`runtime-test-record.schema.json`](runtime-test-record.schema.json) | `record_version` **1.0** | Authorized runtime test records (not passive default) |
| [`structured-claim.schema.json`](structured-claim.schema.json) | (object) | Intermediate AI auditor claims |

---

## Guard scan JSON (convention-validated)

`authdiff scan` writes additional documents validated by tooling conventions:

| Artifact | Documented in |
| --- | --- |
| `findings.json` | [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md), [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md) |
| `inventory.json` | [`../docs/COVERAGE-MATRIX.md`](../docs/COVERAGE-MATRIX.md) |
| `baseline.json` / `risk-delta.json` | [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md) |
| `findings.sarif.json` | SARIF 2.1.0 via `authdiff.export.sarif` |

---

## Semantic validation

JSON Schema compliance is necessary but not sufficient. `authdiff-dev validate report|graph`
also runs semantic checks (orphan evidence, duplicate ids, dangling graph refs).
See [`../docs/archive/architecture/ADR-002-semantic-validation.md`](../docs/archive/architecture/ADR-002-semantic-validation.md).
