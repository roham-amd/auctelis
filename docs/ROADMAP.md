# auctelis roadmap

**Product:** The authority lockfile and PR review for what AI agents can reach.

**Positioning:** GitHub-native Authority Diff + enforcement gate. Locally,
`auctelis check` is the repo preflight. Host hooks / allow store / tripwires
are removed.

**Current:** **0.1.9** · lock schema 1 · tooling 0.1.9

## North star (Gate Zero)

1. One extractor, one diff, one PR comment, one Action (lock optional)
2. Lockless six-line workflow first; `init --enforce` when ready to fail closed
3. Adoption ceremony is `BASELINE_ADOPTED`, never false `PASS`
4. Empty baseline is fine: first growth under enforce is CODEOWNERS review
5. Coverage and evidence strength are visible on every match and card
6. Product path is **tree-truth**; research scanner is `auctelis_research` (not in wheel)
7. Comment posts when authority changed (opt into every-PR); required check fails on **tier≥fail** reach only when locked

## Release line

| Version | Work | Status |
| --- | --- | --- |
| **0.1.0** | Initial release: reach check, lock, gate, Action, Reach Report, `check --github` | **done** |
| **0.1.1** | Green Release assets + calm lock digests + executable org Watch rollout | **done** |
| **0.1.2** | PyPI-ready CTAs, agent-only CI precision, inline Pin fix + org-reusable rollout | **done** |
| **0.1.3** | Pasteable Pin fix, headline-first Reach Report, PyPI cutover guards (still `pypi_live=false`) | **done** |
| **0.1.4** | Arg-preserving Pin fix, tier-2 demo agent CI, cross-platform `auctelis rollout` (still `pypi_live=false`) | **done** |
| **0.1.5** | Evidence-backed `rollout`, live PR `Pin fix` parity, zero-install org audit Action (still `pypi_live=false`) | **done** |
| **0.1.6** | Funnel ledger (`rollout --status`), fleet audit memory (`--baseline`), opt-in resolved pins (still `pypi_live=false`) | **done** |
| **0.1.7** | Zero-laptop org-audit cron/status/resolved-pin parity + SHA-pinned Watch rollout (still `pypi_live=false`) | **done** |
| **0.1.8** | Org-audit PR-read + Drift Issue + offline `--action-sha` / surface diet (still `pypi_live=false`) | **done** |
| **0.1.9** | Tier-1+ Drift Issue + enforce SHA-pin parity + single-install org-audit (still `pypi_live=false`) | **done** |
| Next | Feature freeze. Concierge: 10 external org audits → `rollout --apply --pin-sha` → day-14 `--status`. Hold `rollout --fix-pins` (**AUCT-056**) until day-14 Watch merge rate <30%. PyPI cutover only if ≥3 pilots ask. Research repo split if unused | open |

## 30-day concierge sprint (now)

| Window | Work | Done when |
| --- | --- | --- |
| Days 1–3 | Ship **AUCT-055** + **AUCT-057**; feature-freeze CLI | Tests green; Drift Issue silent on Watch merges; `init --owner --enforce --action-sha` works |
| Days 1–30 | 10 external org audits (CLI or `auctelis-org-audit.yml`); log `TRACKER.md` + `pilot-metrics.csv` | ≥10 outside reach reports |
| Days 7–14 | Open Watch PRs with `rollout --apply --pin-sha`; measure with `--status` | Day-14 merge rate known |
| Day 14 gate | Build **AUCT-056** (`rollout --fix-pins`) **only if** Watch merge rate <30% | Flag shipped or explicitly skipped |
| Day 30 | ≥5 outside repos `watching_on_default` | Day-60 gate still open |

Kill speculative CLI expansion (`why` / `trust` / `diff --base` / lock ceremony / research rules) until five outside repos retain the Action.

## 90-day decision gate

| Signal at day 60 | Action |
| --- | --- |
| ≥5 outside repos retain the gate weekly, and ≥3 growth PRs were code-owner-reviewed | Continue; consider GitHub App only on pull |
| Kill criterion fails | Stop feature work; publish [`PLAYBOOK.md`](PLAYBOOK.md) + benchmark; archive CLI |

Do not add a web app, MCP server, certification badge, marketplace, or egress
broker before five outside repos retain the gate.

## Kill list (product path)

- Host `watch` / `allow` / `hook` / `doctor` / `ledger` / `host_scan` / plugins
- Public 22-rule scanner in the product wheel (moved to `auctelis_research`)
- `vet`, `harden`, `explain`, audit/ecosystem-graph as product gate inputs
- Docker as the Authority Diff install story
- Circular “PyPI waits for five pilots” rule (install must work for strangers; cutover is a later maturity bet, not a gate)
- Marketplace listing / badge / “Authority Watch” product copy (root Action is a normal `uses:` Action, not a Marketplace pitch)
- Drift-as-failure and default strict-ruleset on comment-only installs
- Action `locked=false` “growth unchecked” warning
- Treating every CI workflow / Plugin / Subagent as fail-tier
- Legacy Action inputs that neutralized the gate
- `auctelis-dev` in the product wheel (lives in `tools/dev` workspace member)

Keep: `diff --base`, lockless workflow, `rollout`, `init`, `status`, `check` (+ `--report` / `--github`), `lock`, `gate`, `why`, `demo`. Fleet reports lead with `auctelis rollout` (no Bash `rollout-watch-prs.sh`). `ci init` remains a hidden alias.

## Success metrics

- 10 non-dogfood reach reports in 30 days
- Five outside repos with the Action retained for 30 days
- ≥3 growth PRs code-owner-reviewed outside this repository
- Median time-to-first-report under 10 minutes; report→workflow conversion ≥30%
- Known open gate bypasses: 0
