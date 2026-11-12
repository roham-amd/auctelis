# authdiff JSON schemas

Machine-readable contracts for authdiff artifacts.

Canonical **audit report** source of truth:

- Edit: [`../canonical/schemas/audit-report.schema.json`](../canonical/schemas/audit-report.schema.json)
- Publish: `authdiff-dev build schemas` → `audit-report.schema.json` in this directory

Validate instances:

```bash
authdiff-dev validate report path/to/summary.json
```

---

## Product-critical schema

| File | Version | Purpose |
| --- | --- | --- |
| [`authority-lock.schema.json`](authority-lock.schema.json) | lock `version` **1** | **`AUTHORITY.lock`** — approved authority baseline |
| [`authority-policy.schema.json`](authority-policy.schema.json) | policy contract | `.authdiff.yml` gate policy shape |

Semantic contract for the lock (identity, expansion/reduction/representation, pins):
[`../docs/AUTHORITY-LOCK.md`](../docs/AUTHORITY-LOCK.md).

---

## Schema catalog

| File | Version field | Purpose |
| --- | --- | --- |
| [`audit-report.schema.json`](audit-report.schema.json) | `audit_version` **1.0** | Narrative engagement summary JSON (maintainer/corpus) |
| [`ecosystem-graph.schema.json`](ecosystem-graph.schema.json) | `graph_version` **1.0** | Nodes/edges seed from inventory (not exploit proof) |

Removed in 0.3.0–0.3.1: research schemas, agent-authority-manifest, and the
legacy `AI_Agent_Ecosystem_Security_Audit_v1` filename alias.

---

## Guard scan JSON (convention-validated)

`authdiff scan` writes additional documents validated by tooling conventions:

| Artifact | Documented in |
| --- | --- |
| `findings.json` | [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md), [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md) |
| `inventory.json` | [`../docs/COVERAGE-MATRIX.md`](../docs/COVERAGE-MATRIX.md) |
| `authority-sbom.json` | [`../docs/GUARD-SCAN.md`](../docs/GUARD-SCAN.md) |
| `findings.sarif.json` | SARIF 2.1.0 via `authdiff.export.sarif` |

---

## Semantic validation

JSON Schema compliance is necessary but not sufficient. `authdiff-dev validate report`
also runs semantic checks (orphan evidence, duplicate ids).
See [`../docs/EVIDENCE-MODEL.md`](../docs/EVIDENCE-MODEL.md).
