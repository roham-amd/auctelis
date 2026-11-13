# auctelis roadmap

**Product:** package-lock for agent authority — every change to what agents can do is a reviewable diff, enforced by the review rules you already have.

**Current:** 0.3.3 · tooling 0.3.3 · rule pack 1.6 · policy contract 1.3

1. **Lock + gate** — field-level lock diffs; growth labels; GitHub CODEOWNERS/rulesets enforce review (auctelis does not count PR approvals).
2. **Doctor front door** — `auctelis doctor` / `--since-lock`; bare CLI → doctor or scan.
3. **CI Action** — base-ref trust; explicit `BASELINE_ADOPTED` ceremony; `strict-ruleset` for UNVERIFIED.
4. **Evidence** — 25→100 labeled configs (`eval/`); publish FP/FN per release.
5. **Distribution** — PyPI + release assets (wheel/sdist/cosign/SBOM); five outside repos keeping the check 30 days ([`pilots/TRACKER.md`](pilots/TRACKER.md)).
6. **Kill if** no external repo keeps the check enabled by day 60 → fall back to checklist + slash commands ([`PLAYBOOK.md`](PLAYBOOK.md)).

Defer: MCP audit server, web app, marketplace, runtime broker, heavy AgentSecBench claims.

Detail: [`PRODUCT.md`](PRODUCT.md) · [`CHANGELOG.md`](../CHANGELOG.md) · [`EVALUATION-PROTOCOL.md`](EVALUATION-PROTOCOL.md) · [`pilots/`](pilots/).
