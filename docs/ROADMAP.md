# auctelis roadmap

**Product:** The authority lockfile and PR review for what AI agents can reach.

**Positioning:** GitHub-native Authority Diff + enforcement gate. Locally,
`auctelis check` is the repo preflight. Host hooks / allow store / tripwires
are removed.

**Current:** **0.9.1** (material-reach + gate-owned PR comment) · lock schema 1 · tooling 0.9.1

## North star (Gate Zero)

1. One extractor, one lock, one diff, one PR comment, one Action
2. `auctelis init --owner team` configures CODEOWNERS + pins release tag
3. Adoption ceremony is `BASELINE_ADOPTED`, never false `PASS`
4. Empty baseline is fine: first growth is CODEOWNERS review — not hollow /
   forever `FAIL_CLOSED`
5. Coverage and evidence strength are visible on every match and card
6. Product path is **tree-truth**; research scanner stays on `auctelis-dev`
7. Required check fails on **material** reach only; comment always posts

## 30-day build (Gate Zero → 0.9.1)

| Window | Work | Status |
| --- | --- | --- |
| Days 1–3 | Truth reset: stale docs, vocabulary, build guard, dogfood `main` | done |
| Week 1 | Adoption sticky comment; evidence strength; `@ path` on all cards; coverage truth | done |
| Week 2 | `ci init --apply`; `diff --base`; pin Action to commit SHA | done |
| Week 3 | Effective-rules endpoint; base CODEOWNERS trust; gate trust tests | done |
| Week 4 | Ship 0.8.0; host stack + public scanner removed; 25-config fixture suite | done |
| **0.8.1** | Consumer Action pin; empty-baseline growth; `init`/`status`; inventory-only product path | **done** |
| **0.8.2** | Trust reset: no fail_on promotion; Action inventory-only; CODEOWNERS protection; unparsed fail-closed; evidence through diff; PyPI-ready docs | **done** |
| **0.9.0** | Tree-truth gate; lock↔tree drift; prose hosts; init CODEOWNERS for authority paths; Docker removed | **done** |
| **0.9.1** | Gate-owned PR comment; material-reach fail; `status --check` requires verified ruleset; docs/Action defaults aligned | **done** |
| Next | PyPI Trusted Publishing; five outside pilots; physical scanner delete from wheel | open |

## 90-day decision gate

| Signal at day 60 | Action |
| --- | --- |
| ≥5 outside repos retain the gate weekly, and ≥3 growth PRs were code-owner-reviewed | Continue; consider GitHub App only on pull |
| Kill criterion fails | Stop feature work; publish [`PLAYBOOK.md`](PLAYBOOK.md) + benchmark; archive CLI |

Do not add a web app, MCP server, certification badge, marketplace, or egress
broker before five outside repos retain the gate.

## Kill list (product path)

- Host `watch` / `allow` / `hook` / `doctor` / `ledger` / `host_scan` / plugins
- Public 22-rule scanner, `vet`, `harden`, `explain`, audit/ecosystem-graph schemas
- Docker as the Authority Diff install story (removed in 0.9.0)
- PyPI ceremony until five pilots retain the gate
- Marketplace / badge / “Authority Watch” product copy

Keep: `init`, `status`, `check`, `lock`, `ci`, `gate`, `why`, `demo`, `diff --base`.

## Success metrics

- Five outside repos with the Action required on the default branch for 30 days
- ≥3 growth PRs code-owner-reviewed outside this repository
- Median time-to-first-delta under 10 minutes
- Known open gate bypasses: 0
