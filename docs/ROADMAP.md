# auctelis roadmap

**Product:** Evidence-backed trust dossiers for MCP servers, skills, hooks, and plugins.

**Positioning:** Trust Dossier (`inspect` / `inspect --local`) + local Authority
Diff (`diff --base`). Legacy lockfile / gate / fleet CLIs are `auctelis-dev`
only. Host hooks / allow store / tripwires are removed.

**Current:** **0.1.11** · lock schema 1 · tooling 0.1.11 · public path `inspect` + `diff`

## North star (Gate Zero)

1. One Trust Dossier front door; one Authority Diff; one Action
2. Zero-install dossiers (`dossiers/CATALOG.json` + IssueOps) before any lock ceremony
3. Adoption ceremony is `BASELINE_ADOPTED`, never false `PASS`
4. Empty baseline is fine: first growth under enforce is CODEOWNERS review
5. Coverage and evidence strength are visible on every match and card
6. Product path is **inspect + diff**; research scanner is `auctelis_research` (not in wheel)
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
| **0.1.10** | Org-audit exit-1 tolerance + SHA-pin fleet CTAs + realistic sample report (still `pypi_live=false`) | **done** |
| **0.1.11** | Trust Dossier front door (`inspect` / `--local` / IssueOps), core rules in wheel, public CLI shrink to `inspect`+`diff`, remove rollout/org-fleet (still `pypi_live=false`) | **done** |

| Next | Concierge: Trust Dossier aha via `inspect` / IssueOps; PyPI cutover only if ≥3 pilots ask. Research repo split if unused | open |

## 30-day concierge sprint (now)

| Window | Work | Done when |
| --- | --- | --- |
| Days 1–2 | Ship **AUCT-060** + **AUCT-061** (defect-only; fleet headline / org-scoped baselines) | Tests green; no speculative CLI |
| Days 1–3 | **AUCT-058** + **AUCT-059** shipped in 0.1.10; feature-freeze CLI (AUCT-055/057 done in 0.1.9) | Sample report shows Pin fix |
| Days 3–30 | Trust-dossier pilots (`inspect` + IssueOps); log `TRACKER.md` + `pilot-metrics.csv` | ≥10 outside dossiers |
| Days 7–14 | Action retained on pilot repos via Authority Diff | Day-14 installs known |
| Day 30 | ≥5 outside repos retain the Action | Day-60 gate still open |

Kill speculative CLI expansion until five outside repos retain the Action.

## 90-day decision gate

| Signal at day 60 | Action |
| --- | --- |
| ≥5 outside repos retain the gate weekly, and ≥3 growth PRs were code-owner-reviewed | Continue; consider GitHub App only on pull |
| Kill criterion fails | Stop feature work; publish [`PLAYBOOK.md`](PLAYBOOK.md) + benchmark; archive CLI |

Do not add a web app, MCP server, certification badge, marketplace, or egress
broker before five outside repos retain the gate.

## Kill list (product path)

- Host `watch` / `allow` / `hook` / `doctor` / `ledger` / `host_scan` / plugins
- Public full-tree `scan` / `annotate` CLIs in the product wheel (rules ship for `inspect`; research scanner stays `auctelis_research` / `auctelis-dev`)
- `vet`, `harden`, `explain`, audit/ecosystem-graph as product gate inputs
- Docker as the Authority Diff install story
- Circular “PyPI waits for five pilots” rule (install must work for strangers; cutover is a later maturity bet, not a gate)
- Marketplace listing / badge / “Authority Watch” product copy (root Action is a normal `uses:` Action, not a Marketplace pitch)
- Drift-as-failure and default strict-ruleset on comment-only installs
- Action `locked=false` “growth unchecked” warning
- Treating every CI workflow / Plugin / Subagent as fail-tier
- Legacy Action inputs that neutralized the gate
- `auctelis-dev` in the product wheel (lives in `tools/dev` workspace member)
- Public `check` / `lock` / `gate` / `init` / `rollout` / `trust` / `why` / `demo` (moved to `auctelis-dev`)

Keep: `inspect`, `inspect --local`, `diff --base`.

## Success metrics

- 10 non-dogfood Trust Dossiers in 30 days
- Five outside repos with the Action retained for 30 days
- ≥3 growth PRs code-owner-reviewed outside this repository
- Median time-to-first-dossier under 10 minutes
- Known open gate bypasses: 0
