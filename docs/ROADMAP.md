# auctelis roadmap

**Product:** The authority lockfile and PR review for what AI agents can reach.

**Positioning:** GitHub-native Authority Diff + enforcement gate. Locally,
`auctelis check` is the repo preflight. Host hooks / allow store / tripwires
are removed.

**Current:** **0.16.0** (one-file lockless install + fleet reach report + fail-closed/status honesty fixes) · lock schema 1 · tooling 0.16.0

## North star (Gate Zero)

1. One extractor, one diff, one PR comment, one Action (lock optional)
2. Lockless six-line workflow first; `init --enforce` when ready to fail closed
3. Adoption ceremony is `BASELINE_ADOPTED`, never false `PASS`
4. Empty baseline is fine: first growth under enforce is CODEOWNERS review
5. Coverage and evidence strength are visible on every match and card
6. Product path is **tree-truth**; research scanner is `auctelis_research` (not in wheel)
7. Comment posts when authority changed (opt into every-PR); required check fails on **tier≥fail** reach only when locked

## 30-day build (applied in 0.11.0)

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
| **0.9.1** | Gate-owned PR comment; material-reach fail; `status --check` requires verified ruleset | **done** |
| **0.10.0** | Lockless default; reach tiers; tomllib; CODEOWNERS path fix; research out of wheel; dogfood/release matrix | **done** |
| **0.11.0** | Lean Action (`uv sync --no-editable`); remove locked=false warning; `--comment-only` gate; CI/Plugin/Subagent paging fix; status comment-only OK; doc pin reset; wheel-smoke research omit | **done** |
| **0.12.0** | Agent Reach Review: day-zero `diff --base` (`BASELINE_NEEDED`); honest comment-only verdict; quiet-on-NONE; ranked reach report; env/tier on cards; offline enforce status; trusted destinations; MCP pin doctor | **done** |
| **0.12.1** | PyPI one-line install (superseded by the 0.13.0 install-truth guard; `pypi_live=false`); first-run "watching" comment; prose inference capped at comment tier; two-surface docs | **done** |
| **0.12.2** | Real-repo CI/TOML signal fix; quiet-PR silence + working `BASELINE_ADOPTED`; shallow fast lockless Action; working `uvx --from` install | **done** |
| **0.13.0** | Install truth (`pypi_live` guard); Reach Report (`check --report`); enforce integrity (lock delete / legacy inputs / first-run / trust / truncation); org reusable workflow | **done** |
| **0.13.1** | Reseal dogfood `AUTHORITY.lock` after 0.13.0 workflow edits; keep CI check green | **done** |
| **0.13.2** | LF-stable authority digests across Windows and Linux | **done** |
| **0.13.3** | Release pipeline installs `auctelis-dev` before metadata verify / SBOM | **done** |
| **0.14.0** | Complete Reach Report; lockless tree-truth `diff --base`; honest install-PR Watching; monorepo walk limits; lean Action (drop deprecated research inputs) | **done** |
| **0.15.0** | Live install-PR Watching bugfix; pure tree-truth `diff --base`; product wheel diet (`auctelis_devtools`); lockless funnel CTA | **done** |
| **0.16.0** | One-file `init --lockless`; fleet reach report; honest coverage/pins/terminal rendering; fail-closed truncation + lockless `status`; research/dev modules out of the wheel | **done** |
| Next | Five outside pilots (report-first); flip `pypi_live` after Trusted Publishing; research repo split if unused | open |

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
- Docker as the Authority Diff install story (removed in 0.9.0)
- Circular “PyPI waits for five pilots” rule (killed in 0.13 — install must work for strangers)
- Marketplace / badge / “Authority Watch” product copy
- Drift-as-failure and default strict-ruleset on comment-only installs
- Action `locked=false` “growth unchecked” warning (removed in 0.11.0)
- Treating every CI workflow / Plugin / Subagent as fail-tier (fixed in 0.11.0)
- Legacy Action inputs that neutralized the gate (`baseline` skipping auth-diff; warn-and-ignore in 0.13, delete in 0.14)
- `auctelis-dev` in the product wheel (moved to `tools/dev` workspace member)

Keep: `diff --base`, lockless workflow, `init`, `status`, `check` (+ `--report`), `lock`, `ci`, `gate`, `why`, `demo`.

## Success metrics

- 10 non-dogfood reach reports in 30 days
- Five outside repos with the Action retained for 30 days
- ≥3 growth PRs code-owner-reviewed outside this repository
- Median time-to-first-report under 10 minutes; report→workflow conversion ≥30%
- Known open gate bypasses: 0
