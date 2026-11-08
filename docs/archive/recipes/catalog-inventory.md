# Recipe: catalog inventory (Stages 0–2)

1. Set `AUDIT_SCOPE_MODE=catalog_inventory` and `EXTERNAL_SOURCE_SCOPE=repository_only`.
2. Run passive discovery: `aesa inventory /path/to/catalog -o repository-inventory.json`.
3. Load `01-core-prompt.md` + guardrails; reconcile inventory with Phase 2 manual review.
4. Produce narrative + JSON with `repository_decision=ECOSYSTEM_INVENTORY_ONLY`.
5. Validate JSON: `aesa validate report security-audit-summary.json`.

Do not deep-audit linked repos without explicit authorization entries.
