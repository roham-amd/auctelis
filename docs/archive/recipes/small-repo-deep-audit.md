# Recipe: small repo selected-component deep audit

1. Define scope manifest (`examples/sample-audit-manifest.yaml` as template).
2. Pin target commit SHA in audit inputs; record `environment_mode`.
3. `aesa inventory` + Phase 2–4 procedure with applicable `modules/*.md`.
4. Build interaction graph JSON (`schemas/ecosystem-graph.schema.json`); run `aesa validate graph` and optional `aesa graph paths`.
5. Complete JSON summary; set `json_validation_status=VALIDATED` only after `aesa validate report`.

Runtime claims require separately authorized staging — keep `trust_chain.runtime_behavior_tested=false` for passive audits.
