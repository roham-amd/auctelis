# auctelis roadmap

**Product:** The authority lockfile and PR review for what AI agents can reach.

**Positioning:** GitHub-native Authority Diff + enforcement gate. Locally,
`auctelis check` is the repo preflight. Host hooks / allow store / tripwires
are archived.

**Current:** 0.7.0 → shipping **0.7.0** · lock schema 1 · tooling 0.7.0

## North star (direction #1)

1. One extractor, one lock, one diff, one PR comment, one Action
2. Enforce-by-default (`locked=true`); `--advisory` opt-out
3. Full project discovery (MCP, skills, instructions, rules, agents, hooks)

## 30-day build (Authority Diff)

| Window | Work | Status |
| --- | --- | --- |
| Days 1–3 | Freeze front door; `check` repo-only; archive allow/hooks; fix 0.5.0 docs | done |
| Week 1 | Full project discovery; `authority-diff/1`; dogfood lock | done |
| Week 2 | `ci init` enforce + CODEOWNERS; Action `locked` default true | done |
| Week 3 | PR cards with file path; eval scaffold; recruit five outside repos | in progress |
| Week 4 | Ship 0.7.0; shrink public docs; kill-list cleanup | in progress |

## 90-day decision gate

| Signal at day 60 | Action |
| --- | --- |
| ≥5 repos with the check enabled weekly, or ≥3 growth PRs reviewed | Continue; consider GitHub App only on pull |
| Fewer than five repos / three reviewed growth PRs | Stop feature work; publish [`PLAYBOOK.md`](PLAYBOOK.md) + benchmark; archive CLI |

Do not add a 23rd rule, a badge, a web app, or an egress broker before five
outside repos run the check.

## Kill list (product path)

- Host hooks / heartbeat / `hook status` / plugin bundles as the front door
- `allow` store / Project Trust as the headline
- Scanner / SARIF / 22-rule gate as the public product
- Audit / ecosystem-graph schemas in the public story
- Docker / PyPI ceremony until 10 active teams (git-tag install stays honest)
- Calling anything a sandbox, broker, or certification

## Success metrics

- Minutes from install → first PR Authority Diff (target under 10)
- Repos with the check enabled weekly
- Share of growth PRs with CODEOWNER review
- False-positive rate on 25 real repos
- Unparsed gaps fixed

Detail: [`PRODUCT.md`](PRODUCT.md) · [`REACH.md`](REACH.md) · [`CHANGELOG.md`](../CHANGELOG.md)
