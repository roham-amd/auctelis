# auctelis JSON schemas

## Product-critical (public)

| File | Version | Purpose |
| --- | --- | --- |
| [`authority-lock.schema.json`](authority-lock.schema.json) | lock `version` **1** | **`AUTHORITY.lock`** — the lockfile standard |

Reach definition: [`../docs/REACH.md`](../docs/REACH.md)  
Semantic contract: [`../docs/AUTHORITY-LOCK.md`](../docs/AUTHORITY-LOCK.md)

---

## Maintainer / demoted (not the product story)

| File | Purpose |
| --- | --- |
| [`authority-policy.schema.json`](authority-policy.schema.json) | `.auctelis.yml` (optional team gate) |
| [`audit-report.schema.json`](audit-report.schema.json) | Maintainer/corpus narrative (canonical edit under `canonical/schemas/`) |
| [`ecosystem-graph.schema.json`](ecosystem-graph.schema.json) | Inventory graph seed — not a public claim |

`auctelis scan` may still write `findings.json` / SARIF; those are annotation
artifacts, not the Authority Watch product.
