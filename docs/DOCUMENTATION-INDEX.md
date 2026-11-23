# Documentation index (auctelis 0.1.11)

Two surfaces — Trust Dossier (`inspect` / `inspect --local`) and Authority Diff
(`diff --base` + the Action) — plus **six** public pages. Everything else is
maintainer or reference depth; it is not part of the first ten minutes.

## Public surface (6)

| Doc | Purpose |
| --- | --- |
| [`../README.md`](../README.md) | Trust Dossier front door (`inspect` + Action) |
| [`INSTALL.md`](INSTALL.md) | Git-tag install (PyPI planned) + first-run `inspect` |
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
| [`SECURITY-RULES.md`](SECURITY-RULES.md) | Rules 001–022 (core wheel + `auctelis-dev scan`) |
| [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md) | Evidence classes |
| [`TRUST-AND-SAFETY.md`](TRUST-AND-SAFETY.md) | Audit-process trust |
| [`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) | FP/FN labeling |
| [`auctelis-consumer-gate.example.yml`](auctelis-consumer-gate.example.yml) | CI recipe |
| [`../dossiers/CATALOG.json`](../dossiers/CATALOG.json) | Zero-install dossier index |
| [`examples/`](examples/) | Static sample Reach Report (evaluate before install) |
| [`pilots/`](pilots/) | Pilot tracker (dossier-first) |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Release notes |
| [`../SECURITY.md`](../SECURITY.md) | Vulnerability reporting |

Skill (explainer only): [`../skills/auctelis-auditor/SKILL.md`](../skills/auctelis-auditor/SKILL.md)
