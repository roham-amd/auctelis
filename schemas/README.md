# authdiff JSON schemas

Machine-readable contracts for authdiff artifacts.

Canonical **audit report** source of truth:

- Edit: [`../canonical/schemas/audit-report.schema.json`](../canonical/schemas/audit-report.schema.json)
- Publish aliases: `authdiff-dev build schemas` → this directory

Validate instances:

```bash
authdiff-dev validate report path/to/summary.json
```

---

## Product-critical schema

| File | Version | Purpose |
| --- | --- | --- |
| [`authority-lock.schema.json`](authority-lock.schema.json) | lock `version` **1** | **`AUTHORITY.lock`** — approved authority baseline (north-star artifact) |
| [`authority-policy.schema.json`](authority-policy.schema.json) | policy contract | `.authdiff.yml` / gate policy shape |
| [`agent-authority-manifest.schema.json`](agent-authority-manifest.schema.json) | `authdiff.authority_manifest.v1` | Declared vs observed Agent Authority Manifest (legacy) |

Semantic contract for the lock (identity, expansion/reduction/representation, pins):
[`../docs/AUTHORITY-LOCK.md`](../docs/AUTHORITY-LOCK.md).

---

## Schema catalog

| File | Version field | Purpose |
| --- | --- | --- |
| [`audit-report.schema.json`](audit-report.schema.json) | `audit_version` **1.0** | Narrative engagement summary JSON |
| [`AI_Agent_Ecosystem_Security_Audit_v1.schema.json`](AI_Agent_Ecosystem_Security_Audit_v1.schema.json) | same | Legacy filename alias |
| [`ecosystem-graph.schema.json`](ecosystem-graph.schema.json) | `graph_version` **1.0** | Nodes/edges/attack_paths seed |

Unused research schemas (audit-manifest, audit-diff, evidence-digest-manifest,
runtime-test-record, structured-claim) were removed in 0.3.0.

---

## Guard scan JSON (convention-validated)

`authdiff scan` writes additional documents validated by tooling conventions:

| Artifact | Documented in |
| --- | --- |
| `findings.json` | [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md), [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md) |
| `inventory.json` | [`../docs/COVERAGE-MATRIX.md`](../docs/COVERAGE-MATRIX.md) |
| `findings.sarif.json` | SARIF 2.1.0 via `authdiff.export.sarif` |

---

## Semantic validation

JSON Schema compliance is necessary but not sufficient. `authdiff-dev validate report`
also runs semantic checks (orphan evidence, duplicate ids).
See [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md).
