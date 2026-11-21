# Documentation index (auctelis 0.1.6)

Three surfaces — `check` locally (including `--report` / `--github`), `rollout`
(Watch PRs + `--status` funnel ledger), and the Action on later PRs — plus
**six** public pages. Everything else is maintainer or reference depth; it is
not part of the first ten minutes.

## Public surface (6)

| Doc | Purpose |
| --- | --- |
| [`../README.md`](../README.md) | Three-surface front door (`check` + `rollout` + Action) |
| [`INSTALL.md`](INSTALL.md) | Git-tag install (PyPI planned) + `check --report` + org audit Action |
| [`PRODUCT.md`](PRODUCT.md) | Frozen product contract |
| [`REACH.md`](REACH.md) | Reach definition, tiers, and Shareable Reach Report layout |
| [`AUCTELIS-GATE.md`](AUCTELIS-GATE.md) | Enforce Action + CODEOWNERS |
| [`AUTHORITY-LOCK.md`](AUTHORITY-LOCK.md) | Lock semantics, diff classes |

## Maintainer / reference depth

| Doc | Purpose |
| --- | --- |
| [`CLI-REFERENCE.md`](CLI-REFERENCE.md) | Full CLI (`auctelis-dev` for maintainer) |
| [`PLAYBOOK.md`](PLAYBOOK.md) | Human review checklist (day-60 fallback) |
| [`ROADMAP.md`](ROADMAP.md) | 30/90-day plan + kill list |
| [`POLICY.md`](POLICY.md) | `.auctelis.yml` |
| [`COVERAGE-MATRIX.md`](COVERAGE-MATRIX.md) | Adapter maturity |
| [`adapters/`](adapters/) | Per-surface maturity specs |
| [`GUARD-SCAN.md`](GUARD-SCAN.md) | Maintainer annotation (`auctelis-dev`; not product gate) |
| [`SECURITY-RULES.md`](SECURITY-RULES.md) | Rules 001–022 (maintainer / auctelis-dev) |
| [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md) | Evidence classes |
| [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md) | Audit-process trust |
| [`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) | FP/FN labeling |
| [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml) | CI recipe |
| [`auctelis-org-audit.yml`](auctelis-org-audit.yml) | Zero-install org Reach Audit (`workflow_dispatch`; weekly drift via prior artifact) |
| [`auctelis-org-reusable.yml`](auctelis-org-reusable.yml) | Org `workflow_call` template |
| [`pilots/`](pilots/) | Five-pilot tracker (report-first) |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Release notes |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability reporting |

Skill (explainer only): [`../skills/auctelis-auditor/SKILL.md`](../skills/auctelis-auditor/SKILL.md)
