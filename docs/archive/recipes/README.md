# Assessment recipes

Practical engagement patterns for authdiff (Authority Diff). Prefer
`aesa doctor` → `aesa vet` → `aesa scan` when tooling is available, then deepen
with the auditor skill.

| Recipe | Doc |
| --- | --- |
| Authority Diff first assessment (default) | [`guard-first-assessment.md`](guard-first-assessment.md) |
| Docker + AI agent (Cursor / Claude / Codex / …) | [`../docker-agent-audit.md`](../docker-agent-audit.md) |
| Catalog / awesome-list inventory | [`catalog-inventory.md`](catalog-inventory.md) |
| Small repo deep audit | [`small-repo-deep-audit.md`](small-repo-deep-audit.md) |
| Source-only review | [`source-only-review.md`](source-only-review.md) |
| Staging / runtime boundary | [`staging-boundary.md`](staging-boundary.md) |

## Shared prerequisites

1. Authorization and scope (`docs/usage.md`)
2. Passive guardrails (`archive/methodology/prompts/04-passive-guardrails.md`)
3. Guard scan artifacts (`docs/GUARD-SCAN.md`) when possible
4. Evidence discipline (`docs/EVIDENCE-MODEL.md`)
5. Matching modules only (`modules/README.md`)

All examples are synthetic patterns — adapt scope, authorization, and limitations to each engagement.

Docs index: [`../DOCUMENTATION-INDEX.md`](../DOCUMENTATION-INDEX.md).
